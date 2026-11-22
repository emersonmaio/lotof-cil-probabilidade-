"""V7 co-occurrence portfolio model for Lotofácil.

Research model only: all scores are computed from contests strictly before
the target contest. Validation selects the configuration; holdout is untouched.
"""
import argparse, csv, json, math, random, statistics
from pathlib import Path

NUMS = tuple(range(1, 26))
K = 15
PAIRS = tuple((i, j) for i in NUMS for j in NUMS if i < j)

CONFIGS = {
    "V7-A": {"windows":[10,30,75,150], "weights":[.35,.30,.20,.15],
             "recency_weight":.18, "pair_weight":.15, "pair_novelty":.20,
             "overlap_penalty":.55},
    "V7-B": {"windows":[10,30,75,150], "weights":[.35,.30,.20,.15],
             "recency_weight":.18, "pair_weight":.25, "pair_novelty":.30,
             "overlap_penalty":.55},
    "V7-C": {"windows":[20,50,100,200], "weights":[.35,.30,.20,.15],
             "recency_weight":.12, "pair_weight":.20, "pair_novelty":.25,
             "overlap_penalty":.55},
    "V7-D": {"windows":[20,50,100,200], "weights":[.10,.20,.30,.40],
             "recency_weight":.08, "pair_weight":.25, "pair_novelty":.25,
             "overlap_penalty":.75},
}

def load(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if len(row) < 17 or not row[0].strip().isdigit():
                continue
            c = int(row[0])
            d = tuple(sorted(int(x) for x in row[2:17]))
            if len(d) != 15 or len(set(d)) != 15 or not all(1 <= x <= 25 for x in d):
                raise ValueError(c)
            rows.append((c, d))
    return sorted(rows)

def individual_scores(history, cfg):
    out = []
    for n in NUMS:
        fs = 0.0
        for w, weight in zip(cfg["windows"], cfg["weights"]):
            h = history[-w:]
            fs += weight * (sum(n in d for _, d in h) + 1) / (w + 2)
        lag = len(history) + 1
        for i in range(len(history)-1, -1, -1):
            if n in history[i][1]:
                lag = len(history) - i
                break
        out.append((1-cfg["recency_weight"]) * fs + cfg["recency_weight"] / lag)
    return out

def pair_scores(history, cfg):
    result = {p: 0.0 for p in PAIRS}
    for w, weight in zip(cfg["windows"], cfg["weights"]):
        h = history[-w:]
        counts = {n: 0 for n in NUMS}
        pairs = {p: 0 for p in PAIRS}
        for _, draw in h:
            s = set(draw)
            for n in s:
                counts[n] += 1
            for p in PAIRS:
                if p[0] in s and p[1] in s:
                    pairs[p] += 1
        for p in PAIRS:
            # Smoothed PMI, shrunk strongly when the window is small.
            pi = (counts[p[0]] + 1) / (w + 2)
            pj = (counts[p[1]] + 1) / (w + 2)
            pij = (pairs[p] + 1) / (w + 1)
            pmi = math.log(max(pij / max(pi * pj, 1e-12), 1e-12))
            shrink = math.sqrt(w / (w + 50.0))
            result[p] += weight * max(-1.0, min(1.0, pmi * shrink))
    return result

def weighted_game(weights, rng):
    pool = {n:max(weights[n-1], 1e-12) for n in NUMS}
    out = []
    for _ in range(K):
        total = sum(pool.values())
        x = rng.random() * total
        acc = 0.0
        for n, w in list(pool.items()):
            acc += w
            if acc >= x:
                out.append(n)
                del pool[n]
                break
    return tuple(sorted(out))

def game_score(game, indiv, pair, cfg):
    base = sum(math.log(indiv[n-1] + 1e-12) for n in game)
    vals = [pair[(a,b)] for a,b in PAIRS if a in game and b in game]
    pair_term = statistics.mean(vals) if vals else 0.0
    return base + cfg["pair_weight"] * pair_term

def portfolio(history, rng, config="V7-B", candidates=220):
    cfg = CONFIGS[config]
    indiv = individual_scores(history, cfg)
    pair = pair_scores(history, cfg)
    seen = set()
    cand = []
    while len(cand) < candidates:
        g = weighted_game(indiv, rng)
        if g in seen:
            continue
        seen.add(g)
        cand.append((game_score(g, indiv, pair, cfg), g))
    chosen = []
    covered = set()
    while len(chosen) < 10:
        best = None
        best_u = -1e99
        for score, g in cand:
            if any(g == x[1] for x in chosen):
                continue
            gs = set(g)
            overlap = sum(len(gs & set(x[1])) for x in chosen)
            novelty = sum(max(0.0, pair[p]) for p in PAIRS
                          if p[0] in gs and p[1] in gs and p not in covered)
            utility = score - cfg["overlap_penalty"] * overlap + cfg["pair_novelty"] * novelty
            if utility > best_u:
                best_u = utility
                best = (score, g)
        chosen.append(best)
        covered.update(p for p in PAIRS if p[0] in best[1] and p[1] in best[1])
    return [g for _, g in chosen]

def evaluate(rows, start, end, config, seed):
    by = {c:d for c,d in rows}
    rng = random.Random(seed)
    vals = []
    for c in range(start, end+1):
        history = [x for x in rows if x[0] < c]
        target = set(by[c])
        vals.append(max(len(set(g) & target) for g in portfolio(history, rng, config)))
    return vals

def metrics(v):
    return {
        "contests": len(v),
        "mean_best": round(sum(v)/len(v), 6),
        "median_best": statistics.median(v),
        "std_best": round(statistics.pstdev(v), 6),
        "11_plus": sum(x >= 11 for x in v),
        "12_plus": sum(x >= 12 for x in v),
        "13_plus": sum(x >= 13 for x in v),
        "14_plus": sum(x >= 14 for x in v),
        "15": sum(x >= 15 for x in v),
        "max": max(v),
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="results/v7")
    p.add_argument("--validation-start", type=int, default=2275)
    p.add_argument("--validation-end", type=int, default=3032)
    p.add_argument("--holdout-start", type=int, default=3033)
    p.add_argument("--holdout-end",type=int,default=None)
    p.add_argument("--seed", type=int, default=20261002)
    a = p.parse_args()
    rows = load(a.csv)
    a.holdout_end = a.holdout_end or rows[-1][0]
    Path(a.out).mkdir(parents=True, exist_ok=True)
    validation = {k: metrics(evaluate(rows, a.validation_start, a.validation_end, k, a.seed))
                  for k in CONFIGS}
    selected = max(CONFIGS, key=lambda k:(validation[k]["13_plus"], validation[k]["mean_best"]))
    holdout = metrics(evaluate(rows, a.holdout_start, a.holdout_end, selected, a.seed+1000))
    report = {"validation":validation, "selected":selected, "holdout":holdout}
    Path(a.out, "v7_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
