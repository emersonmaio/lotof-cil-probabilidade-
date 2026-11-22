"""Congela portfólios prospectivos da Lotofácil antes de o resultado-alvo ser conhecido.

Garantias desta versão (ver docs/AUDITORIA_2026-11-19.md):
- o histórico precisa terminar exatamente em alvo-1 (sem lacunas);
- um arquivo congelado existente NUNCA é sobrescrito;
- se o último concurso do histórico é antigo demais (o alvo provavelmente já foi
  sorteado), o congelamento é recusado, a menos que --allow-retroactive seja usado;
  nesse caso o arquivo sai marcado como retroativo (prospective=false) e não pode ser
  contado como avaliação prospectiva;
- cada arquivo recebe SHA-256 do CSV usado e é registrado em MANIFEST.jsonl (append-only).
O resultado do alvo nunca é lido.
"""
import argparse
import hashlib
import json
import os
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import diversified
import optimized_structure
from data_io import load_history, sha256_file
from v6_probabilistic import CONFIGS as V6_CONFIGS, portfolio as v6_portfolio
from v7_1_optimized import CONFIGS as V7_CONFIGS, prefix_state, score_state, portfolio as v7_portfolio
from v8_adaptive import make_candidates, choose10

DEFAULT_MAX_STALENESS_DAYS = 4  # Lotofácil sorteia de segunda a sábado (às vezes domingo)
V6_V7_CANDIDATES = 220


def generate_games(rows, seed, v8_candidates):
    """Gera todos os portfólios usando apenas `rows` (concursos anteriores ao alvo)."""
    history = [(c, d) for c, d, _ in rows]
    rng = random.Random(seed)
    games = {}
    for cfg in V6_CONFIGS:
        games[cfg] = [list(g) for g in v6_portfolio(history, rng, cfg, candidates=V6_V7_CANDIDATES)]
    numpref, pairpref, last = prefix_state(rows)
    i = len(rows)
    for cfg, params in V7_CONFIGS.items():
        indiv, pair = score_state(i, params, numpref, pairpref, last)
        games[cfg] = [list(item[1]) for item in v7_portfolio(indiv, pair, rng, params, candidates=V6_V7_CANDIDATES)]
    for cfg, params in V7_CONFIGS.items():
        indiv, pair = score_state(i, params, numpref, pairpref, last)
        cands = make_candidates(indiv, pair, params, rng, v8_candidates)
        games["V8-" + cfg] = [list(item[1]) for item in choose10(cands, pair, params)]
    random_games, seen = [], set()
    while len(random_games) < 10:
        g = tuple(sorted(rng.sample(range(1, 26), 15)))
        if g not in seen:
            seen.add(g)
            random_games.append(list(g))
    games["ALEATORIO"] = random_games
    # controle adicionado DEPOIS do aleatório: não altera o consumo de RNG dos portfólios anteriores
    games["DIVERSIFICADO"] = [diversified.mask_to_game(m) for m in diversified.choose(rng)]
    games["OTIMIZADO"] = [diversified.mask_to_game(m) for m in optimized_structure.choose(rng)]
    return games


def build_record(csv_path, target, seed, candidates, now=None, max_staleness_days=DEFAULT_MAX_STALENESS_DAYS,
                 allow_retroactive=False):
    now = now or datetime.now(timezone.utc)
    hist = load_history(csv_path)
    if hist[-1][0] >= target:
        raise ValueError("O histórico precisa terminar antes do concurso-alvo.")
    if hist[-1][0] != target - 1:
        raise ValueError(f"Histórico termina em {hist[-1][0]}, mas alvo é {target}; verifique concursos faltantes.")
    last_date = hist[-1][2]
    stale = (now.date() - last_date).days if last_date else None
    retro = stale is None or stale > max_staleness_days
    if retro and not allow_retroactive:
        raise ValueError(
            f"Congelamento recusado: o último concurso do histórico ({hist[-1][0]}) é de {last_date} "
            f"({stale} dias antes de hoje). O concurso-alvo {target} provavelmente já foi sorteado; "
            "congelar agora seria retroativo. Atualize o CSV com os resultados oficiais até o último "
            "concurso REALIZADO e congele o PRÓXIMO. Use --allow-retroactive apenas para teste "
            "(o arquivo sairá marcado como não prospectivo)."
        )
    rows = [(c, d, sum(1 << (n - 1) for n in d)) for c, d, _ in hist]
    # semente efetiva = base + alvo: com semente fixa, ALEATORIO e DIVERSIFICADO saíam IDÊNTICOS em todos
    # os concursos (confirmado em auditoria), o que tira o poder de calibração dos controles.
    effective_seed = seed + target
    games = generate_games(rows, effective_seed, candidates)
    return {
        "target_contest": target,
        "history_through": hist[-1][0],
        "history_last_date": last_date.isoformat() if last_date else None,
        "staleness_days_at_generation": stale,
        "prospective": not retro,
        "generated_at_utc": now.isoformat(),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "data_sha256": sha256_file(csv_path),
        "python": platform.python_version(),
        "seed_base": seed,
        "seed": effective_seed,
        "candidate_count_v8": candidates,
        "candidate_count_v6_v7": V6_V7_CANDIDATES,
        "rule": "All portfolios generated using contests strictly lower than target; do not regenerate after result.",
        "games": games,
    }


def write_frozen(record, out_dir):
    """Grava o registro SEM sobrescrever e acrescenta ao manifesto append-only."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = "" if record["prospective"] else "_RETROATIVO"
    path = out / f"concurso_{record['target_contest']}_congelado{suffix}.json"
    existing = list(out.glob(f"concurso_{record['target_contest']}_congelado*.json"))
    if existing:
        raise FileExistsError(
            f"Já existe registro congelado para o concurso {record['target_contest']}: {existing[0].name}. "
            "Registros congelados são imutáveis e não podem ser regenerados."
        )
    payload = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    with open(path, "x", encoding="utf-8") as f:  # 'x' falha se o arquivo já existir
        f.write(payload)
    entry = {
        "file": path.name,
        "target_contest": record["target_contest"],
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "generated_at_utc": record["generated_at_utc"],
        "prospective": record["prospective"],
    }
    with open(out / "MANIFEST.jsonl", "a", encoding="utf-8") as m:
        m.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def verify_manifest(out_dir):
    """Confere o SHA-256 de cada arquivo listado no manifesto. Devolve lista de problemas."""
    out = Path(out_dir)
    problems = []
    mf = out / "MANIFEST.jsonl"
    if not mf.exists():
        return problems
    for line in mf.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        p = out / e["file"]
        if not p.exists():
            problems.append(f"{e['file']}: arquivo ausente")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != e["sha256"]:
            problems.append(f"{e['file']}: conteúdo alterado após o congelamento")
    return problems


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--target", type=int, required=True)
    p.add_argument("--out", default="results/frozen")
    p.add_argument("--seed", type=int, default=20261019)
    p.add_argument("--candidates", type=int, default=300)
    p.add_argument("--max-staleness-days", type=int, default=DEFAULT_MAX_STALENESS_DAYS)
    p.add_argument("--allow-retroactive", action="store_true")
    p.add_argument("--verify-only", action="store_true", help="apenas verifica o manifesto existente")
    a = p.parse_args()
    problems = verify_manifest(a.out)
    if problems:
        print("FALHA de integridade dos registros congelados:\n  " + "\n  ".join(problems), file=sys.stderr)
        sys.exit(2)
    if a.verify_only:
        print("Manifesto íntegro.")
        return
    try:
        record = build_record(a.csv, a.target, a.seed, a.candidates,
                              max_staleness_days=a.max_staleness_days, allow_retroactive=a.allow_retroactive)
        path = write_frozen(record, a.out)
    except (ValueError, FileExistsError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Congelado: {path} (prospective={record['prospective']})")


if __name__ == "__main__":
    main()
