"""V7 multi-seed stability audit.

Configuration selection is made on validation only. Each selected configuration
is then evaluated once on the untouched holdout.
"""
import argparse, json, statistics
from pathlib import Path
from v7_cooccurrence import CONFIGS, evaluate, load, metrics

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="results/v7")
    p.add_argument("--validation-start", type=int, default=2275)
    p.add_argument("--validation-end", type=int, default=3032)
    p.add_argument("--holdout-start", type=int, default=3033)
    p.add_argument("--holdout-end", type=int, default=3794)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--seed-base", type=int, default=20261002)
    a = p.parse_args()
    rows = load(a.csv)
    records = []
    for i in range(a.seeds):
        seed = a.seed_base + i * 1009
        validation = {k: metrics(evaluate(rows, a.validation_start, a.validation_end, k, seed))
                      for k in CONFIGS}
        selected = max(CONFIGS, key=lambda k:(validation[k]["13_plus"], validation[k]["mean_best"]))
        holdout = metrics(evaluate(rows, a.holdout_start, a.holdout_end, selected, seed+1000))
        records.append({"seed":seed, "selected":selected, "validation":validation, "holdout":holdout})
    means = [r["holdout"]["mean_best"] for r in records]
    p13 = [r["holdout"]["13_plus"] for r in records]
    summary = {
        "seeds": a.seeds,
        "validation_range": [a.validation_start, a.validation_end],
        "holdout_range": [a.holdout_start, a.holdout_end],
        "mean_best_avg": round(statistics.mean(means), 6),
        "mean_best_std": round(statistics.pstdev(means), 6),
        "13_plus_avg": round(statistics.mean(p13), 6),
        "13_plus_std": round(statistics.pstdev(p13), 6),
        "selection_counts": {k:sum(r["selected"]==k for r in records) for k in CONFIGS},
        "runs": records,
    }
    Path(a.out).mkdir(parents=True, exist_ok=True)
    Path(a.out, "v7_stability.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
