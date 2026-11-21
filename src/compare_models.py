"""Comparação V6 x V7.1 x V8 x baseline aleatório sob condições idênticas.

Desenho (definido ANTES de olhar os resultados):
- mesmos concursos (holdout 3033..último), mesmos 10 jogos por concurso para todos;
- o pipeline de cada versão é o do repositório: por semente, a configuração é escolhida
  SOMENTE na validação (2275-3032) pela regra da própria versão e avaliada uma vez no holdout;
- hipótese nula H0: o sorteio é uniforme e independente do passado. Para cada concurso e cada
  portfólio congelado, a distribuição do "melhor jogo" sob H0 é estimada contra R sorteios
  aleatórios (pool comum, semente fixa). Isso dá, por concurso, E_c e Var_c exatos o bastante
  e dispensa comparar com um baseline empírico ruidoso: a diferença (obs - E_c) é
  uma diferença de martingale sob H0, logo Z = soma(obs-E_c)/raiz(soma Var_c) ~ N(0,1);
- o baseline aleatório passa pelo MESMO procedimento e serve de calibração (Z deve ser ~N(0,1));
- estabilidade: blocos consecutivos de 100 concursos;
- sem ajuste de parâmetros usando o holdout; nenhuma métrica aqui escolhe configuração.
"""
import argparse
import json
import math
import random
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import diversified
import experiment
import v6_probabilistic as v6
import v7_1_optimized as v71
import v8_adaptive as v8
from data_io import load_history, sha256_file

VAL = (2275, 3032)
HOLD_START = 3033
NULL_R = 4000
BLOCK = 100
MODELS = ("V6", "V7.1", "V8", "RANDOM", "DIVERSIFIED")


def mask(game):
    m = 0
    for n in game:
        m |= 1 << (n - 1)
    return m


# ---------------------------------------------------------------- geração de portfólios
# Cada função replica EXATAMENTE o consumo de RNG do `evaluate` do repositório
# (verificado em tests/test_compare_fidelity.py), mas devolve os jogos.

def portfolios_v6(rows6, start, end, cfg, seed, candidates=180):
    rng = random.Random(seed)
    return [[mask(g) for g in v6.portfolio([x for x in rows6 if x[0] < c], rng, cfg, candidates)]
            for c in range(start, end + 1)]


def portfolios_v71(rows71, states, start, end, cfg, seed, candidates=220):
    rng = random.Random(seed)
    params = v71.CONFIGS[cfg]
    out = []
    for c in range(start, end + 1):
        indiv, pair = states[c][cfg]
        out.append([g[2] for g in v71.portfolio(indiv, pair, rng, params, candidates)])
    return out


def portfolios_v8(rows71, states, start, end, cfg, seed, candidates=300):
    rng = random.Random(seed)
    params = v71.CONFIGS[cfg]
    out = []
    for c in range(start, end + 1):
        indiv, pair = states[c][cfg]
        games = v8.choose10(v8.make_candidates(indiv, pair, params, rng, candidates), pair, params)
        out.append([g[2] for g in games])
    return out


def portfolios_random(start, end, seed):
    rng = random.Random(seed)
    return [[mask(g) for g in experiment.portfolio([], rng, "random10", 0)] for _ in range(start, end + 1)]


def portfolios_diversified(start, end, seed, candidates=180, overlap_penalty=0.55):
    """Controle "só diversificação" (ver diversified.py)."""
    rng = random.Random(seed)
    return [diversified.choose(rng, candidates, overlap_penalty) for _ in range(start, end + 1)]


# ---------------------------------------------------------------- avaliação
def best_hits(portfolios, draws_mask):
    return [max(bin(g & draws_mask[c]).count("1") for g in games)
            for c, games in zip(range(len(portfolios)), portfolios)]


def metrics_from_best(best):
    n = len(best)
    return {
        "contests": n,
        "mean_best": round(sum(best) / n, 6),
        "13_plus": sum(b >= 13 for b in best), "12_plus": sum(b >= 12 for b in best),
        "11_plus": sum(b >= 11 for b in best), "14_plus": sum(b >= 14 for b in best),
        "15": sum(b >= 15 for b in best),
        "median_best": statistics.median(best), "std_best": round(statistics.pstdev(best), 6),
        "max": max(best)
    }


def null_pool(seed=1234, r=NULL_R):
    rng = random.Random(seed)
    return np.array([mask(rng.sample(range(1, 26), 15)) for _ in range(r)], dtype=np.uint32)


def null_stats(portfolios, pool):
    """Por concurso: E[melhor], Var[melhor] e P(melhor>=k) sob H0 (sorteio uniforme)."""
    n = len(portfolios)
    E = np.empty(n); V = np.empty(n); P = {k: np.empty(n) for k in (11, 12, 13, 14)}
    for i, games in enumerate(portfolios):
        g = np.array(games, dtype=np.uint32)[:, None]
        hits = np.bitwise_count(g & pool[None, :]).max(axis=0)
        E[i] = hits.mean(); V[i] = hits.var()
        for k in P:
            P[k][i] = (hits >= k).mean()
    return E, V, P


def test_vs_null(best, E, V, P):
    best = np.asarray(best)
    n = len(best)
    diff = float((best - E).sum() / n)
    se = float(math.sqrt(V.sum()) / n)
    out = {"mean_best_obs": round(float(best.mean()), 6), "mean_best_null": round(float(E.mean()), 6),
           "diff": round(diff, 6), "se": round(se, 6), "z": round(diff / se, 3),
           "ci95": [round(diff - 1.96 * se, 6), round(diff + 1.96 * se, 6)]}
    for k, p in P.items():
        obs = int((best >= k).sum()); exp = float(p.sum()); var = float((p * (1 - p)).sum())
        out[f"null_{k}_plus"] = {"obs": obs, "expected": round(exp, 2), "z": round((obs - exp) / math.sqrt(var), 3) if var > 0 else None}
    # estabilidade por blocos
    blocks = []
    for s in range(0, n, BLOCK):
        sl = slice(s, min(s + BLOCK, n))
        d = float((best[sl] - E[sl]).mean())
        blocks.append(round(d, 4))
    out["block_diffs"] = blocks
    out["blocks_positive"] = int(sum(b > 0 for b in blocks))
    out["blocks_total"] = len(blocks)
    return out


# ---------------------------------------------------------------- uma execução (modelo, semente)
def run_one(args):
    model, seed, csv_path, hold_end, n_cand = args
    t0 = time.time()
    hist = load_history(csv_path)
    rows6 = [(c, d) for c, d, _ in hist]
    rows71 = [(c, d, sum(1 << (n - 1) for n in d)) for c, d, _ in hist]
    dmask = {c: m for c, _, m in rows71}
    pool = null_pool()

    def best_for(portfolios, start):
        return [max((g & dmask[start + i]).bit_count() for g in games) for i, games in enumerate(portfolios)]

    rec = {"model": model, "seed": seed}
    if model == "RANDOM":
        hold = portfolios_random(HOLD_START, hold_end, seed + 2000)
        rec["selected"] = None
    elif model == "DIVERSIFIED":
        hold = portfolios_diversified(HOLD_START, hold_end, seed + 3000)
        rec["selected"] = None
    else:
        if model == "V6":
            cfgs = list(v6.CONFIGS)
            def gen(cfg, s, e, sd): return portfolios_v6(rows6, s, e, cfg, sd)
            key = lambda m: (m["13_plus"], m["mean_best"])
        else:
            states = v71.build_states(rows71, VAL[0], hold_end)
            cfgs = list(v71.CONFIGS)
            if model == "V7.1":
                def gen(cfg, s, e, sd): return portfolios_v71(rows71, states, s, e, cfg, sd)
                key = lambda m: (m["13_plus"], m["mean_best"])
            else:
                def gen(cfg, s, e, sd): return portfolios_v8(rows71, states, s, e, cfg, sd, n_cand)
                key = v8.score_key
        val = {}
        for cfg in cfgs:
            b = best_for(gen(cfg, VAL[0], VAL[1], seed), VAL[0])
            m = v71.metrics(b)
            val[cfg] = m
        selected = max(cfgs, key=lambda k: key(val[k]))
        rec["selected"] = selected
        rec["validation_selected"] = val[selected]
        hold = gen(selected, HOLD_START, hold_end, seed + 1000)
    best = best_for(hold, HOLD_START)
    E, V, P = null_stats(hold, pool)
    rec["holdout"] = {**metrics_from_best(best), **test_vs_null(best, E, V, P)}
    rec["best_per_contest"] = best
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="results/compare")
    ap.add_argument("--hold-end", type=int, default=None, help="padrão: último concurso do CSV")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--seed-base", type=int, default=20261002)
    ap.add_argument("--candidates-v8", type=int, default=300)
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    hist = load_history(a.csv)
    hold_end = a.hold_end or hist[-1][0]
    tasks = [(m, a.seed_base + i * 1009, a.csv, hold_end, a.candidates_v8)
             for m in a.models.split(",") for i in range(a.seeds)]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        runs = list(ex.map(run_one, tasks))
    summary = {"csv_sha256": sha256_file(a.csv), "holdout": [HOLD_START, hold_end], "validation": list(VAL),
               "seeds": a.seeds, "null_draws": NULL_R, "candidates_v8": a.candidates_v8, "models": {}}
    for m in a.models.split(","):
        rs = [r for r in runs if r["model"] == m]
        h = [r["holdout"] for r in rs]
        summary["models"][m] = {
            "selected_counts": {k: sum(r["selected"] == k for r in rs) for k in {r["selected"] for r in rs}},
            "mean_best_avg": round(statistics.mean(x["mean_best_obs"] for x in h), 6),
            "mean_best_seed_sd": round(statistics.pstdev([x["mean_best_obs"] for x in h]), 6),
            "null_mean_best_avg": round(statistics.mean(x["mean_best_null"] for x in h), 6),
            "diff_avg": round(statistics.mean(x["diff"] for x in h), 6),
            "diff_seed_sd": round(statistics.pstdev([x["diff"] for x in h]), 6),
            "se_avg": round(statistics.mean(x["se"] for x in h), 6),
            "z_per_seed": [x["z"] for x in h],
            "13_plus_obs_avg": round(statistics.mean(x["13_plus"] for x in h), 2),
            "13_plus_expected_avg": round(statistics.mean(x["null_13_plus"]["expected"] for x in h), 2),
            "13_plus_z_avg": round(statistics.mean(x["null_13_plus"]["z"] for x in h), 3),
            "blocks_positive_avg": round(statistics.mean(x["blocks_positive"] for x in h), 2),
            "blocks_total": h[0]["blocks_total"],
        }
    Path(a.out).mkdir(parents=True, exist_ok=True)
    Path(a.out, "compare_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    Path(a.out, "compare_runs.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
