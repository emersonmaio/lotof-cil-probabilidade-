"""Otimiza a ESTRUTURA de 10 jogos para maximizar E[melhor jogo] (cobertura), sem usar histórico.

Busca local (subida de encosta com aceitação de empates) sobre uma subamostra fixa de sorteios;
o resultado final é sempre avaliado de forma EXATA em todos os C(25,15) sorteios (exact_eval).
Como a estrutura não usa o histórico, uma permutação aleatória dos 25 números por concurso
(`relabel`) mantém exatamente as mesmas estatísticas e torna os jogos independentes entre concursos.
"""
import argparse
import json
import random
from pathlib import Path

import numpy as np

import diversified
import exact_eval as ex


def mask_to_list(m):
    return [i + 1 for i in range(25) if m >> i & 1]


def random_swap(m, rng, nswap):
    for _ in range(nswap):
        ins = [i for i in range(25) if m >> i & 1]
        outs = [i for i in range(25) if not m >> i & 1]
        m ^= (1 << rng.choice(ins)) | (1 << rng.choice(outs))
    return m


def optimize(start, iters=6000, sample=400_000, seed=1):
    rng = random.Random(seed)
    nprng = np.random.default_rng(seed)
    draws = ex.all_draws()
    sub = draws[nprng.choice(len(draws), size=sample, replace=False)]
    games = list(start)
    H = ex.hits_matrix(games, sub)
    cur = H.max(axis=0).astype(np.float64).mean()
    for it in range(iters):
        i = rng.randrange(len(games))
        cand = random_swap(games[i], rng, rng.choice((1, 1, 2, 3)))
        if cand in games:
            continue
        hn = np.bitwise_count(np.uint32(cand) & sub).astype(np.uint8)
        others = np.delete(H, i, axis=0).max(axis=0)
        val = np.maximum(others, hn).astype(np.float64).mean()
        if val >= cur:
            games[i], H[i], cur = cand, hn, val
    return games


def relabel(games, rng):
    """Permuta os rótulos 1..25 (mesma estrutura, outro conjunto de dezenas)."""
    perm = list(range(25))
    rng.shuffle(perm)
    out = []
    for g in games:
        m = 0
        for i in range(25):
            if g >> i & 1:
                m |= 1 << perm[i]
        out.append(m)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/optimized")
    ap.add_argument("--iters", type=int, default=6000)
    ap.add_argument("--starts", type=int, default=3)
    a = ap.parse_args()
    best, best_e = None, -1
    for s in range(a.starts):
        rng = random.Random(100 + s)
        start = diversified.choose(rng) if s == 0 else [ex.mask(rng.sample(range(1, 26), 15)) for _ in range(10)]
        g = optimize(start, a.iters, seed=s + 1)
        e = ex.exact_stats(g)["E_best"]
        print(f"start {s}: E_best exato = {e:.5f}", flush=True)
        if e > best_e:
            best, best_e = g, e
    stats = ex.exact_stats(best)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    rep = {"games": [mask_to_list(m) for m in best], "masks": best, "exact": stats}
    Path(a.out, "optimized_portfolio.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
