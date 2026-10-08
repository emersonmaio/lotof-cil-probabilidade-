"""V8 multi-seed stability audit."""
import argparse,json,statistics
from pathlib import Path
from v7_1_optimized import CONFIGS,build_states,load,metrics
from v8_adaptive import evaluate,score_key
def main():
 p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--out",default="results/v8")
 p.add_argument("--validation-start",type=int,default=2275); p.add_argument("--validation-end",type=int,default=3032)
 p.add_argument("--holdout-start",type=int,default=3033); p.add_argument("--holdout-end",type=int,default=3794)
 p.add_argument("--seeds",type=int,default=5); p.add_argument("--seed-base",type=int,default=20261002)
 p.add_argument("--candidates",type=int,default=1000); a=p.parse_args()
 rows=load(a.csv); Path(a.out).mkdir(parents=True,exist_ok=True); states=build_states(rows,a.validation_start,a.holdout_end); runs=[]
 for i in range(a.seeds):
  seed=a.seed_base+i*1009
  val={k:metrics(evaluate(rows,a.validation_start,a.validation_end,k,seed,states,a.candidates)) for k in CONFIGS}
  sel=max(CONFIGS,key=lambda k:score_key(val[k]))
  hold=metrics(evaluate(rows,a.holdout_start,a.holdout_end,sel,seed+1000,states,a.candidates))
  runs.append({"seed":seed,"selected":sel,"validation":val,"holdout":hold})
 means=[r["holdout"]["mean_best"] for r in runs]; p13=[r["holdout"]["13_plus"] for r in runs]
 out={"engine":"V8","candidates":a.candidates,"seeds":a.seeds,"mean_best_avg":round(statistics.mean(means),6),
 "mean_best_std":round(statistics.pstdev(means),6),"13_plus_avg":round(statistics.mean(p13),6),
 "13_plus_std":round(statistics.pstdev(p13),6),"selection_counts":{k:sum(r["selected"]==k for r in runs) for k in CONFIGS},"runs":runs}
 Path(a.out,"v8_stability.json").write_text(json.dumps(out,indent=2),encoding="utf-8"); print(json.dumps(out,indent=2))
if __name__=="__main__": main()
