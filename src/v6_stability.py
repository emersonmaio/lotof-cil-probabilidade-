"""V6 multi-seed stability audit.

For each seed, configuration selection uses validation only. The selected
configuration is then evaluated once on the untouched holdout. This prevents
holdout performance from choosing the model.

The script reports per-seed results plus aggregate mean/std and selection counts.
"""
import argparse, json, statistics
from pathlib import Path
from v6_probabilistic import CONFIGS, evaluate, load, metrics

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="results/v6")
    p.add_argument("--validation-start", type=int, default=2275)
    p.add_argument("--validation-end", type=int, default=3032)
    p.add_argument("--holdout-start", type=int, default=3033)
    p.add_argument("--holdout-end",type=int,default=None)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--seed-base", type=int, default=20261002)
    args=p.parse_args()

    rows=load(args.csv)
    args.holdout_end=args.holdout_end or rows[-1][0]
    records=[]
    for i in range(args.seeds):
        seed=args.seed_base + i*1009
        validation={
            k:metrics(evaluate(rows,args.validation_start,args.validation_end,k,seed))
            for k in CONFIGS
        }
        selected=max(CONFIGS,key=lambda k:(validation[k]["13_plus"],validation[k]["mean_best"]))
        holdout=metrics(evaluate(rows,args.holdout_start,args.holdout_end,selected,seed+1000))
        records.append({"seed":seed,"selected":selected,"validation":validation,"holdout":holdout})

    means=[r["holdout"]["mean_best"] for r in records]
    p13=[r["holdout"]["13_plus"] for r in records]
    summary={
        "seeds":args.seeds,
        "validation_range":[args.validation_start,args.validation_end],
        "holdout_range":[args.holdout_start,args.holdout_end],
        "mean_best_avg":round(statistics.mean(means),6),
        "mean_best_std":round(statistics.pstdev(means),6),
        "13_plus_avg":round(statistics.mean(p13),6),
        "13_plus_std":round(statistics.pstdev(p13),6),
        "selection_counts":{k:sum(r["selected"]==k for r in records) for k in CONFIGS},
        "runs":records,
    }
    Path(args.out).mkdir(parents=True,exist_ok=True)
    Path(args.out,"v6_stability.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
