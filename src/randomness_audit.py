"""Auditoria de aleatoriedade do histórico da Lotofácil.

Pergunta: o histórico mostra alguma dependência (entre concursos, entre dezenas, entre posições)
que um modelo pudesse explorar? Se não mostra, modelos de frequência/recência/coocorrência não têm
em que se apoiar.

Método: cada estatística é calculada no histórico real e comparada com a distribuição obtida em
R históricos simulados sob H0 (sorteios uniformes e independentes, mesmo número de concursos).
p-valor Monte Carlo = (1 + #{simulado >= observado}) / (R + 1), unilateral na cauda "mais extrema".
Correção de múltiplas comparações: Holm sobre todos os testes da lista (lista fixa, definida antes).

Testes (todos fixados antes de ver resultados):
 T1 uniformidade das frequências por dezena
 T2 repetição entre concursos consecutivos (sobreposição média com o concurso anterior; esperado 9)
 T3 dependência lag-1 por dezena (P(sai | saiu no anterior) vs a marginal da própria dezena)
 T4 "atraso": taxa de saída segundo o tempo desde a última aparição (1,2,3,4,5+), vs marginal
 T5 soma das dezenas (média e variância)
 T6 paridade (nº de ímpares por sorteio vs hipergeométrica)
 T7 coocorrência de pares (300 pares), ajustada pelas marginais
 T8 posições: uniformidade dezena x posição (só concursos com ordem de sorteio preservada)
 T9 primeira bola sorteada: uniformidade (mesmos concursos)
"""
import argparse
import csv
import json
from math import comb
from pathlib import Path

import numpy as np

from data_io import load_history, sha256_file

N_NUM, K = 25, 15
ODD = np.array([(i + 1) % 2 for i in range(N_NUM)], dtype=bool)


def to_matrix(draws):
    m = np.zeros((len(draws), N_NUM), dtype=bool)
    for i, d in enumerate(draws):
        m[i, [x - 1 for x in d]] = True
    return m


def simulate_matrix(n, rng):
    """n sorteios uniformes de 15 entre 25 (matriz booleana n x 25)."""
    idx = np.argsort(rng.random((n, N_NUM)), axis=1)[:, :K]
    m = np.zeros((n, N_NUM), dtype=bool)
    np.put_along_axis(m, idx, True, axis=1)
    return m


# ------------------------------------------------------------------ estatísticas (maior = mais extremo)
def s_uniform(m):
    c = m.sum(0)
    e = m.shape[0] * K / N_NUM
    return float(((c - e) ** 2).sum() / e)


def s_repeat(m):
    ov = (m[1:] & m[:-1]).sum(1)
    return float(abs(ov.mean() - 9.0) * np.sqrt(len(ov)))


def s_lag1(m):
    """Dependência lag-1 ajustada pela marginal de cada dezena (não confunde com T1)."""
    prev, cur = m[:-1], m[1:]
    pm = m.mean(0)
    tot = 0.0
    for i in range(N_NUM):
        n1 = prev[:, i].sum()
        v = pm[i] * (1 - pm[i])
        if n1 > 0 and v > 0:
            tot += n1 * (cur[prev[:, i], i].mean() - pm[i]) ** 2 / v
    return float(tot)


def lag_matrix(m, cap=5):
    """Tempo (em concursos) desde a última aparição ANTES de cada concurso; limitado a `cap`."""
    n = m.shape[0]
    idx = np.where(m, np.arange(n)[:, None], -1)
    last = np.maximum.accumulate(idx, axis=0)
    prev_last = np.vstack([np.full((1, N_NUM), -1), last[:-1]])
    lag = np.arange(n)[:, None] - prev_last
    lag[prev_last < 0] = cap
    return np.minimum(lag, cap)


def s_lag(m):
    """Taxa de saída por faixa de atraso (1,2,3,4,5+), contra a marginal da própria dezena."""
    lag = lag_matrix(m)[1:]
    cur = m[1:]
    pm = m.mean(0)[None, :] * np.ones_like(cur, dtype=float)
    var = pm * (1 - pm)
    tot = 0.0
    for L in range(1, 6):
        sel = lag == L
        v = var[sel].sum()
        if v > 0:
            tot += ((cur[sel] - pm[sel]).sum()) ** 2 / v
    return float(tot)


def s_sum_mean(m):
    sums = (m * np.arange(1, N_NUM + 1)).sum(1)
    return float(abs(sums.mean() - 195.0) * np.sqrt(len(sums)) / np.sqrt(325.0))


def s_sum_var(m):
    sums = (m * np.arange(1, N_NUM + 1)).sum(1)
    return float(abs(np.log(sums.var(ddof=1) / 325.0)))


_PAR_P = np.array([comb(13, k) * comb(12, K - k) / comb(25, K) for k in range(0, K + 1)])


def s_parity(m):
    odd = (m & ODD).sum(1)
    obs = np.bincount(odd, minlength=K + 1)[:K + 1]
    exp = _PAR_P * len(odd)
    ok = exp > 5
    return float(((obs[ok] - exp[ok]) ** 2 / exp[ok]).sum())


def s_pairs(m):
    """Coocorrência de pares contra o esperado dadas as marginais observadas (ajuste de 1ª ordem)."""
    n = m.shape[0]
    mi = m.astype(np.int32)
    c = mi.T @ mi
    ci = mi.sum(0)
    e = np.outer(ci, ci) / n * ((K - 1) * N_NUM) / (K * (N_NUM - 1))
    iu = np.triu_indices(N_NUM, 1)
    return float(((c[iu] - e[iu]) ** 2 / e[iu]).sum())


def s_position(ordered):
    """ordered: matriz n x 15 com as dezenas NA ORDEM DE SORTEIO (valores 1..25)."""
    n = ordered.shape[0]
    tot = 0.0
    e = n / N_NUM
    for p in range(K):
        c = np.bincount(ordered[:, p] - 1, minlength=N_NUM)
        tot += ((c - e) ** 2 / e).sum()
    return float(tot)


def s_first(ordered):
    n = ordered.shape[0]
    c = np.bincount(ordered[:, 0] - 1, minlength=N_NUM)
    e = n / N_NUM
    return float(((c - e) ** 2 / e).sum())


def simulate_ordered(n, rng):
    return np.argsort(rng.random((n, N_NUM)), axis=1)[:, :K] + 1


TESTS = [
    ("T1_uniformidade_frequencias", s_uniform, "m"),
    ("T2_repeticao_consecutiva", s_repeat, "m"),
    ("T3_dependencia_lag1", s_lag1, "m"),
    ("T4_atraso", s_lag, "m"),
    ("T5a_soma_media", s_sum_mean, "m"),
    ("T5b_soma_variancia", s_sum_var, "m"),
    ("T6_paridade", s_parity, "m"),
    ("T7_coocorrencia_pares", s_pairs, "m"),
    ("T8_posicoes", s_position, "o"),
    ("T9_primeira_bola", s_first, "o"),
]


def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def read_ordered(csv_path):
    """Dezenas na ordem do CSV, apenas das linhas em que a ordem de sorteio foi preservada
    (linha não está em ordem crescente; uma linha crescente por acaso tem probabilidade 1/15!)."""
    out = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            nums = [int(x) for x in row[2:2 + K]]
            if nums != sorted(nums):
                out.append(nums)
    return np.array(out, dtype=int)


def run(csv_path, reps=1000, seed=20261119):
    hist = load_history(csv_path)
    m = to_matrix([d for _, d, _ in hist])
    ordered = read_ordered(csv_path)
    rng = np.random.default_rng(seed)
    obs, sims = {}, {name: [] for name, _, _ in TESTS}
    for name, fn, kind in TESTS:
        obs[name] = fn(m if kind == "m" else ordered)
    for _ in range(reps):
        sm = simulate_matrix(m.shape[0], rng)
        so = simulate_ordered(ordered.shape[0], rng)
        for name, fn, kind in TESTS:
            sims[name].append(fn(sm if kind == "m" else so))
    res = []
    for name, _, _ in TESTS:
        s = np.array(sims[name])
        p = (1 + int((s >= obs[name]).sum())) / (reps + 1)
        res.append({"teste": name, "estatistica": round(obs[name], 4), "sim_mediana": round(float(np.median(s)), 4),
                    "sim_p95": round(float(np.quantile(s, 0.95)), 4), "p_mc": round(p, 4)})
    adj = holm([r["p_mc"] for r in res])
    for r, a in zip(res, adj):
        r["p_holm"] = round(a, 4)
        r["rejeita_H0_5pct"] = bool(a < 0.05)
    return {"csv_sha256": sha256_file(csv_path), "concursos": int(m.shape[0]),
            "concursos_com_ordem_de_sorteio": int(ordered.shape[0]), "reps": reps, "seed": seed,
            "resultados": res,
            "nota": "p_mc com R=%d tem resolução mínima %.4f; Holm sobre %d testes." % (reps, 1 / (reps + 1), len(res))}


def exploratory_eras(csv_path, reps=400, seed=7, size=1000):
    """DESCRITIVO e post hoc (não entra na correção de Holm): T1 por períodos e frequência por dezena."""
    hist = load_history(csv_path)
    m = to_matrix([d for _, d, _ in hist])
    rng = np.random.default_rng(seed)
    eras = []
    for a in range(0, m.shape[0], size):
        sub = m[a:a + size]
        if sub.shape[0] < size // 2:
            continue
        obs = s_uniform(sub)
        sims = [s_uniform(simulate_matrix(sub.shape[0], rng)) for _ in range(reps)]
        eras.append({"periodo": f"{a + 1}-{a + sub.shape[0]}", "estatistica": round(obs, 2),
                     "sim_mediana": round(float(np.median(sims)), 2),
                     "p_mc": round((1 + sum(x >= obs for x in sims)) / (reps + 1), 4)})
    freq = (m.mean(0) * 100).round(2).tolist()
    se = (0.24 / m.shape[0]) ** 0.5 * 100
    z = [round((f - 60) / se, 2) for f in freq]
    return {"T1_por_periodo": eras, "frequencia_pct_dezenas_1_a_25": freq, "z_vs_60pct": z,
            "aviso": "Exploratório e post hoc: serve para descrever onde está a não-uniformidade, não para inferência."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="results/randomness")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261119)
    a = ap.parse_args()
    rep = run(a.csv, a.reps, a.seed)
    rep["exploratorio"] = exploratory_eras(a.csv)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    Path(a.out, "randomness_audit.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
