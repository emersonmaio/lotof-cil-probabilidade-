"""Pontua o registro congelado de um concurso depois que o resultado oficial entra no histórico.

Garantias:
- só pontua registros com prospective=true e cujo manifesto (SHA-256) está íntegro;
- o histórico usado no congelamento tem de continuar idêntico (hash do prefixo do CSV);
- o registro tem de ter sido gerado antes do horário do sorteio (corte conservador: 22:00 UTC = 19:00 BRT
  do dia do concurso). O horário gravado no registro é autodeclarado: a prova forte é a data do commit no Git;
- cada concurso é pontuado uma única vez (results/prospective/LOG.jsonl é append-only).
Também gera results/prospective/SUMMARY.md com Z por portfólio contra o nulo (config/preregistration.json).
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

import compare_models as cm
from data_io import load_history
from freeze_portfolio import verify_manifest

PRE_DRAW_CUTOFF_UTC_HOUR = 22
BLOCK = 25


def prefix_sha256(csv_path, last_contest):
    lines = Path(csv_path).read_bytes().splitlines(keepends=True)
    return hashlib.sha256(b"".join(lines[: last_contest + 1])).hexdigest()   # cabeçalho + concursos 1..last


def score_contest(csv_path, contest, frozen_dir, out_dir, now=None, pool=None):
    frozen_dir, out_dir = Path(frozen_dir), Path(out_dir)
    hist = load_history(csv_path)
    if contest > hist[-1][0]:
        raise ValueError(f"O concurso {contest} ainda não está no histórico.")
    path = frozen_dir / f"concurso_{contest}_congelado.json"
    if not path.exists():
        raise FileNotFoundError(f"Não há registro congelado prospectivo para o concurso {contest}.")
    problems = verify_manifest(frozen_dir)
    if problems:
        raise ValueError("Manifesto inválido: " + "; ".join(problems))
    rec = json.loads(path.read_text(encoding="utf-8"))
    if not rec.get("prospective"):
        raise ValueError("Registro não prospectivo não pode ser pontuado.")
    if rec["history_through"] != contest - 1:
        raise ValueError("Registro inconsistente: history_through != concurso-1.")
    if prefix_sha256(csv_path, contest - 1) != rec["data_sha256"]:
        raise ValueError("O histórico anterior ao concurso foi alterado depois do congelamento.")
    draw_date = hist[contest - 1][2]
    gen = datetime.fromisoformat(rec["generated_at_utc"])
    cutoff = datetime(draw_date.year, draw_date.month, draw_date.day, PRE_DRAW_CUTOFF_UTC_HOUR, tzinfo=timezone.utc)
    if gen >= cutoff:
        raise ValueError(f"Registro gerado em {gen.isoformat()}, depois do corte pré-sorteio {cutoff.isoformat()}.")
    log = out_dir / "LOG.jsonl"
    if log.exists() and any(json.loads(l)["contest"] == contest for l in log.read_text(encoding="utf-8").splitlines() if l.strip()):
        raise FileExistsError(f"Concurso {contest} já foi pontuado.")
    draw = cm.mask(hist[contest - 1][1])
    pool = pool if pool is not None else cm.null_pool()
    models = {}
    for name, games in rec["games"].items():
        masks = [cm.mask(g) for g in games]
        hits = [(m & draw).bit_count() for m in masks]
        E, V, _ = cm.null_stats([masks], pool)
        models[name] = {"hits": hits, "best": max(hits), "mean_hits": round(sum(hits) / len(hits), 4),
                        "null_E_best": round(float(E[0]), 5), "null_Var_best": round(float(V[0]), 5)}
    entry = {"contest": contest, "draw": list(hist[contest - 1][1]), "frozen_file": path.name,
             "frozen_generated_at_utc": rec["generated_at_utc"], "scored_at_utc": (now or datetime.now(timezone.utc)).isoformat(),
             "models": models}
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def summarize(out_dir, prereg_path):
    out_dir = Path(out_dir)
    log = out_dir / "LOG.jsonl"
    entries = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()] if log.exists() else []
    prereg = json.loads(Path(prereg_path).read_text(encoding="utf-8"))
    primary, controls = prereg["bracos_primarios"], prereg["controles"]
    n = len(entries)
    names = sorted({m for e in entries for m in e["models"]})
    rows = []
    for m in names:
        d = np.array([e["models"][m]["best"] - e["models"][m]["null_E_best"] for e in entries if m in e["models"]])
        v = np.array([e["models"][m]["null_Var_best"] for e in entries if m in e["models"]])
        k = len(d)
        diff = float(d.mean())
        se = float(np.sqrt(v.sum()) / k)
        blocks = [float(d[i:i + BLOCK].mean()) for i in range(0, k, BLOCK)]
        role = "primário" if m in primary else "controle" if m in controls else "exploratório"
        rows.append((m, role, k, diff, se, diff / se if se else float("nan"),
                     sum(b > 0 for b in blocks), len(blocks)))
    thr, need = prereg["limiar_z_bonferroni"], prereg["minimo_de_concursos_prospectivos"]
    lines = ["# Avaliação prospectiva (gerado por src/score_frozen.py)", "",
             f"Concursos prospectivos pontuados: **{n}** (mínimo para concluir: {need}).", "",
             "| Portfólio | Papel | n | Diferença vs. nulo | EP | Z | Blocos de 25 positivos |", "|---|---|---:|---:|---:|---:|---|"]
    for m, role, k, diff, se, z, pos, tot in rows:
        lines.append(f"| {m} | {role} | {k} | {diff:+.4f} | {se:.4f} | {z:+.2f} | {pos}/{tot} |")
    lines.append("")
    if n < need:
        lines.append(f"**Conclusão: insuficiente** — faltam {need - n} concursos. Nenhum resultado desta tabela é evidência.")
    else:
        prom = [m for m, role, k, diff, se, z, pos, tot in rows if role == "primário" and z >= thr and pos > tot / 2]
        lines.append("**Conclusão:** " + (f"braços promissores (Z>={thr}, maioria dos blocos positiva): {', '.join(prom)}. "
                     "Replicar em novo período antes de qualquer afirmação." if prom else "sem vantagem demonstrada."))
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--contest", type=int, help="concurso a pontuar (omita para só gerar o resumo)")
    ap.add_argument("--frozen", default="results/frozen")
    ap.add_argument("--out", default="results/prospective")
    ap.add_argument("--prereg", default="config/preregistration.json")
    a = ap.parse_args()
    try:
        if a.contest:
            e = score_contest(a.csv, a.contest, a.frozen, a.out)
            print(f"Concurso {a.contest} pontuado:", {k: v["best"] for k, v in e["models"].items()})
        summarize(a.out, a.prereg)
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
