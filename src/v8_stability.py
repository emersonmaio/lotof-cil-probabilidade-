"""V8 multi-seed stability audit with a fair random-portfolio baseline."""
import argparse, json, random, statistics
from pathlib import Path
from v7_1_optimized import CONFIGS, build_states, load, metrics
from v8_adaptive import evaluate, score_key


def random_portfolio_best(rows, start, end, seed):
    """Best hits among 10 independent random 15-number tickets per target draw."""
    by = {c: set(draw) for c, draw, _ in rows}
    rng = random.Random(seed)
    vals = []
    for contest in range(start, end + 1):
        target = by[contest]
        best = 0
        for _ in range(10):
            ticket = set(rng.sample(range(1, 26), 15))
            best = max(best, len(ticket & target))
        vals.append(best)
    return vals


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="results/v8")
    p.add_argument("--validation-start", type=int, default=2275)
    p.add_argument("--validation-end", type=int, default=3032)
    p.add_argument("--holdout-start", type=int, default=3033)
    p.add_argument("--holdout-end",type=int,default=None)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--seed-base", type=int, default=20261002)
    p.add_argument("--candidates", type=int, default=300)
    a = p.parse_args()

    rows = load(a.csv)
    a.holdout_end = a.holdout_end or rows[-1][0]
    Path(a.out).mkdir(parents=True, exist_ok=True)
    states = build_states(rows, a.validation_start, a.holdout_end)
    runs = []
    for i in range(a.seeds):
        seed = a.seed_base + i * 1009
        val = {
            k: metrics(evaluate(rows, a.validation_start, a.validation_end, k, seed, states, a.candidates))
            for k in CONFIGS
        }
        selected = max(CONFIGS, key=lambda k: score_key(val[k]))
        hold = metrics(evaluate(rows, a.holdout_start, a.holdout_end, selected, seed + 1000, states, a.candidates))
        random_hold = metrics(random_portfolio_best(rows, a.holdout_start, a.holdout_end, seed + 2000))
        runs.append({
            "seed": seed,
            "selected": selected,
            "validation": val,
            "holdout": hold,
            "random_baseline_holdout": random_hold,
            "mean_best_delta_vs_random": round(hold["mean_best"] - random_hold["mean_best"], 6),
            "13_plus_delta_vs_random": hold["13_plus"] - random_hold["13_plus"],
        })

    means = [r["holdout"]["mean_best"] for r in runs]
    p13 = [r["holdout"]["13_plus"] for r in runs]
    random_means = [r["random_baseline_holdout"]["mean_best"] for r in runs]
    random_p13 = [r["random_baseline_holdout"]["13_plus"] for r in runs]
    out = {
        "engine": "V8",
        "candidates": a.candidates,
        "seeds": a.seeds,
        "validation_range": [a.validation_start, a.validation_end],
        "holdout_range": [a.holdout_start, a.holdout_end],
        "baseline": "10 uniformly random tickets per contest; same holdout dates",
        "mean_best_avg": round(statistics.mean(means), 6),
        "mean_best_std": round(statistics.pstdev(means), 6),
        "13_plus_avg": round(statistics.mean(p13), 6),
        "13_plus_std": round(statistics.pstdev(p13), 6),
        "random_mean_best_avg": round(statistics.mean(random_means), 6),
        "random_mean_best_std": round(statistics.pstdev(random_means), 6),
        "random_13_plus_avg": round(statistics.mean(random_p13), 6),
        "mean_best_delta_vs_random": round(statistics.mean(means) - statistics.mean(random_means), 6),
        "13_plus_delta_vs_random": round(statistics.mean(p13) - statistics.mean(random_p13), 6),
        "selection_counts": {k: sum(r["selected"] == k for r in runs) for k in CONFIGS},
        "runs": runs,
    }
    Path(a.out, "v8_stability.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
