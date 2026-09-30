"""Stage 2 - portfolio coverage test for Lotofacil.

Hypothesis:
- Game 1-8: independent random coverage.
- Game 9-10: greedy complementary games that minimize overlap with the
  first eight and with each other.
- Compare against 10 independent random games using the same seeds.
- Validation is reported separately from the final holdout.
"""
import argparse, csv, json
from pathlib import Path
import numpy as np

K = 15
N = 25
SEEDS = list(range(100, 120))

def load(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        for row in r:
            if row and row[0].strip().lower() == "concurso":
                break
        for row in r:
            if len(row) >= 17 and row[0].strip().isdigit():
                c = int(row[0])
                d = tuple(sorted(int(x) for x in row[2:17]))
                if len(d) != 15 or len(set(d)) != 15 or not all(1 <= x <= 25 for x in d):
                    raise ValueError(f"Linha invalida no concurso {c}")
                rows.append((c, d))
    rows.sort()
    if [c for c, _ in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("Concursos ausentes ou fora de sequencia")
    return dict(rows)

def random_game(rng):
    return tuple(sorted((rng.choice(N, K, replace=False) + 1).tolist()))

def weighted_game(weights, rng):
    p = np.maximum(weights, 0.0)
    p = p / p.sum()
    return tuple(sorted((rng.choice(N, K, replace=False, p=p) + 1).tolist()))

def random10(rng):
    out, seen = [], set()
    while len(out) < 10:
        g = random_game(rng)
        if g not in seen:
            seen.add(g)
            out.append(g)
    return out

def rand8_cov2(rng, candidates=12):
    out, seen = [], set()

    # First eight are deliberately non-adaptive random coverage games.
    while len(out) < 8:
        g = random_game(rng)
        if g not in seen:
            seen.add(g)
            out.append(g)

    # Last two games target numbers that are under-covered by the first eight.
    coverage = np.zeros(N)
    for g in out:
        coverage[np.array(g) - 1] += 1

    for _ in range(2):
        weights = 1.0 / (1.0 + coverage)
        candidates_found = []
        for _ in range(candidates):
            g = weighted_game(weights, rng)
            if g in seen:
                continue
            overlap = sum(len(set(g) & set(h)) for h in out)
            candidates_found.append((overlap, g))
        if not candidates_found:
            g = random_game(rng)
            while g in seen:
                g = random_game(rng)
        else:
            g = min(candidates_found, key=lambda x: (x[0], x[1]))[1]
        seen.add(g)
        out.append(g)
        coverage[np.array(g) - 1] += 1
    return out

def portfolio(name, rng):
    if name == "random10":
        return random10(rng)
    if name == "rand8_cov2":
        return rand8_cov2(rng)
    raise ValueError(name)

def evaluate(by_id, start, end, name, seed):
    # The RNG is deterministic and identical across strategies for paired
    # comparisons, apart from the strategy-specific stream offset.
    offset = sum(ord(x) for x in name) * 1009
    rng = np.random.default_rng(seed + offset)
    vals = []
    for c in range(start, end + 1):
        target = set(by_id[c])
        vals.append(max(len(set(g) & target) for g in portfolio(name, rng)))
    return vals

def seed_metrics(vals):
    a = np.asarray(vals)
    return {
        "mean": float(a.mean()),
        "15": int((a >= 15).sum()),
        "14_plus": int((a >= 14).sum()),
        "13_plus": int((a >= 13).sum()),
        "12_plus": int((a >= 12).sum()),
        "11_plus": int((a >= 11).sum()),
        "10_plus": int((a >= 10).sum()),
        "median": float(np.median(a)),
        "std": float(a.std()),
        "min": int(a.min()),
        "max": int(a.max()),
    }

def bootstrap_ci(values, seed=20260930, B=10000):
    rng = np.random.default_rng(seed)
    a = np.asarray(values, dtype=float)
    idx = rng.integers(0, len(a), size=(B, len(a)))
    means = a[idx].mean(axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]

def compare(a, b):
    keys = ["13_plus", "12_plus", "11_plus", "14_plus", "mean"]
    out = {}
    for k in keys:
        diffs = [x[k] - y[k] for x, y in zip(a, b)]
        out[k] = {
            "paired_seed_delta_mean": float(np.mean(diffs)),
            "bootstrap_ci95": bootstrap_ci(diffs),
        }
    return out

def run_split(by_id, start, end):
    result = {}
    for name in ("random10", "rand8_cov2"):
        per_seed = []
        for seed in SEEDS:
            per_seed.append(seed_metrics(evaluate(by_id, start, end, name, seed)))
        result[name] = {
            "seeds": SEEDS,
            "per_seed": per_seed,
            "aggregate": {
                k: float(np.mean([x[k] for x in per_seed]))
                for k in ["mean", "median", "std", "min", "max"]
            },
            "totals": {
                k: int(sum(x[k] for x in per_seed))
                for k in ["15", "14_plus", "13_plus", "12_plus", "11_plus", "10_plus"]
            },
        }
    result["comparison_rand8_cov2_vs_random10"] = compare(
        result["rand8_cov2"]["per_seed"], result["random10"]["per_seed"]
    )
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="results")
    a = p.parse_args()

    by_id = load(a.csv)
    Path(a.out).mkdir(parents=True, exist_ok=True)

    report = {
        "method": "8 random games + 2 greedy coverage games",
        "seeds": SEEDS,
        "validation": run_split(by_id, 2275, 3032),
        "holdout": run_split(by_id, 3033, 3791),
    }

    with open(Path(a.out) / "stage2.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    lines = [
        "# Stage 2 — 8 + 2 coverage",
        "",
        "Hypothesis: use 8 independent random games and create games 9-10 to fill coverage gaps.",
        "The final holdout is evaluated only after the strategy is fixed.",
        "",
        "| split | strategy | mean | 14+ | 13+ | 12+ | 11+ | 15 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("validation", "holdout"):
        for name in ("random10", "rand8_cov2"):
            r = report[split][name]
            t = r["totals"]
            n = len(SEEDS) * (758 if split == "validation" else 759)
            lines.append(
                f"| {split} | {name} | {r['aggregate']['mean']:.6f} | "
                f"{t['14_plus']} | {t['13_plus']} | {t['12_plus']} | "
                f"{t['11_plus']} | {t['15']} |"
            )
        lines.append("")
    lines += [
        "## Paired bootstrap comparison: rand8_cov2 - random10",
        "",
    ]
    for k, v in report["holdout"]["comparison_rand8_cov2_vs_random10"].items():
        lines.append(
            f"- **{k}**: mean paired delta = {v['paired_seed_delta_mean']:.6f}; "
            f"95% bootstrap CI = [{v['bootstrap_ci95'][0]:.6f}, {v['bootstrap_ci95'][1]:.6f}]"
        )
    lines.append("")
    lines.append("All predictions for each target use only contests before that target.")
    with open(Path(a.out) / "STAGE2.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
