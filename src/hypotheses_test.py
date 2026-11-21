"""Teste walk-forward de hipóteses simples de seleção de dezenas (lista PRÉ-REGISTRADA).

Para cada concurso t (a partir de WARMUP), cada hipótese pontua as 25 dezenas usando SOMENTE
os concursos < t; o bilhete é formado pelas 15 dezenas de maior pontuação (empate: menor dezena).
Sob H0 (sorteio uniforme e independente) o número de acertos desse bilhete tem média 9 e
variância 1,5 (hipergeométrica) para QUALQUER regra decidida antes do sorteio. Logo
Z = (média - 9) / sqrt(1,5/n) ~ N(0,1) e um único bilhete é um teste bem mais potente que "melhor de 10".

Hipóteses (fixas; nenhuma é ajustada com os resultados):
  freq_w (w = 5,10,20,50,100,200), freq_all     -> "quentes": mais frequentes
  cold_w (w = 20,100)                           -> "frias": menos frequentes
  overdue                                       -> mais atrasadas (equivale a 'anti-repetição': as 10 que
                                                   não saíram no anterior + 5 empatadas; por isso não há
                                                   hipótese separada de anti-repetição)
  repeat_prev                                   -> as 15 do concurso anterior
Correção: Bonferroni sobre as K hipóteses (alfa = 0,05/K). Decisão no segmento "todos";
desenvolvimento e holdout são mostrados só para avaliar estabilidade.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from data_io import load_history, sha256_file
from randomness_audit import lag_matrix, to_matrix

WARMUP = 300
DEV_END = 3032      # concursos <= 3032 = desenvolvimento; >= 3033 = holdout (convenção do projeto)
VAR_HITS = 15 * (15 / 25) * (10 / 25) * (10 / 24)   # = 1,5
HYPOTHESES = ["freq_5", "freq_10", "freq_20", "freq_50", "freq_100", "freq_200", "freq_all",
              "cold_20", "cold_100", "overdue", "repeat_prev"]


def scores(m, name):
    """Matriz N x 25 de pontuações; linha t usa apenas m[:t]."""
    n = m.shape[0]
    C = np.vstack([np.zeros((1, m.shape[1]), dtype=np.int64), np.cumsum(m, axis=0)])   # C[t] = soma de m[:t]
    t = np.arange(n)
    if name.startswith("freq_") or name.startswith("cold_"):
        kind, w = name.split("_")
        base = C[t] if w == "all" else C[t] - C[np.maximum(t - int(w), 0)]
        return base.astype(float) if kind == "freq" else -base.astype(float)
    if name == "overdue":
        return lag_matrix(m, cap=10_000).astype(float)
    prev = np.vstack([np.zeros((1, m.shape[1]), dtype=bool), m[:-1]])
    if name == "repeat_prev":
        return prev.astype(float)
    raise ValueError(name)


def top15_hits(m, name, first=WARMUP):
    S = scores(m, name)
    order = np.argsort(-S, axis=1, kind="stable")[:, :15]
    top = np.zeros_like(m)
    np.put_along_axis(top, order, True, axis=1)
    return (top & m).sum(1)[first:]


def z_of(hits):
    n = len(hits)
    mean = float(np.mean(hits))
    se = float(np.sqrt(VAR_HITS / n))
    return {"n": n, "mean_hits": round(mean, 4), "diff_vs_9": round(mean - 9.0, 4), "se": round(se, 4),
            "z": round((mean - 9.0) / se, 3)}


def run(csv_path, first=WARMUP):
    from math import erf, sqrt
    hist = load_history(csv_path)
    m = to_matrix([d for _, d, _ in hist])
    k = len(HYPOTHESES)
    alpha = 0.05 / k
    out = []
    for h in HYPOTHESES:
        hits = top15_hits(m, h, first)
        contests = np.arange(first + 1, m.shape[0] + 1)
        seg = {"todos": hits, "desenvolvimento": hits[contests <= DEV_END], "holdout": hits[contests > DEV_END]}
        res = {"hipotese": h, **{s: z_of(v) for s, v in seg.items()}}
        z = res["todos"]["z"]
        p = 1 - erf(abs(z) / sqrt(2))
        res["p_bilateral_todos"] = round(p, 5)
        res["rejeita_H0_bonferroni"] = bool(p < alpha)
        out.append(res)
    return {"csv_sha256": sha256_file(csv_path), "concursos": int(m.shape[0]), "warmup": first,
            "bonferroni_alpha": round(alpha, 5), "K": k, "resultados": out,
            "nota": "Z>0 = a regra acerta mais que o acaso. Efeito detectável com 80% de poder após Bonferroni (n~3500): ~0,08 acerto no bilhete."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="results/hypotheses")
    a = ap.parse_args()
    rep = run(a.csv)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    Path(a.out, "hypotheses.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
