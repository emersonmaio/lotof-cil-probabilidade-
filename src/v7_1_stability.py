"""V7.1 multi-seed stability audit using cached score states."""
import argparse, json, statistics
from pathlib import Path
from v7_1_optimized import CONFIGS, build_states, evaluate, load, metrics

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True); p.add_argument("--out",default="results/v7_1")
    p.add_argument("--validation-start",type=int,default=2275); p.add_argument("--validation-end",type=int,default=3032)
    p.add_argument("--holdout-start",type=int,default=3033); p.add_argument("--holdout-end",type=int,default=None)
    p.add_argument("--seeds",type=int,default=5); p.add_argument("--seed-base",type=int,default=20261002)
    p.add_argument("--candidates",type=int,default=220)
    a=p.parse_args(); rows=load(a.csv); a.holdout_end=a.holdout_end or rows[-1][0]; Path(a.out).mkdir(parents=True,exist_ok=True)
    states=build_states(rows,a.validation_start,a.holdout_end); records=[]
    for i in range(a.seeds):
        seed=a.seed_base+i*1009
        validation={k:metrics(evaluate(rows,a.validation_start,a.validation_end,k,seed,states,a.candidates)) for k in CONFIGS}
        selected=max(CONFIGS,key=lambda k:(validation[k]["13_plus"],validation[k]["mean_best"]))
        holdout=metrics(evaluate(rows,a.holdout_start,a.holdout_end,selected,seed+1000,states,a.candidates))
        records.append({"seed":seed,"selected":selected,"validation":validation,"holdout":holdout})
    means=[r["holdout"]["mean_best"] for r in records]; p13=[r["holdout"]["13_plus"] for r in records]
    summary={"engine":"V7.1","candidates":a.candidates,"seeds":a.seeds,
      "validation_range":[a.validation_start,a.validation_end],"holdout_range":[a.holdout_start,a.holdout_end],
      "mean_best_avg":round(statistics.mean(means),6),"mean_best_std":round(statistics.pstdev(means),6),
      "13_plus_avg":round(statistics.mean(p13),6),"13_plus_std":round(statistics.pstdev(p13),6),
      "selection_counts":{k:sum(r["selected"]==k for r in records) for k in CONFIGS},"runs":records}
    Path(a.out,"v7_1_stability.json").write_text(json.dumps(summary,indent=2),encoding="utf-8"); print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
