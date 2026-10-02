"""V6 probabilistic portfolio model for Lotofacil."""
import argparse,csv,json,math,random
from pathlib import Path
NUMS=tuple(range(1,26)); K=15
CONFIGS={
"V6-A":{"windows":[20,50,100,200],"weights":[.35,.30,.20,.15],"recency_weight":.12,"overlap_penalty":.55},
"V6-B":{"windows":[20,50,100,200],"weights":[.10,.20,.30,.40],"recency_weight":.08,"overlap_penalty":.55},
"V6-C":{"windows":[10,30,75,150],"weights":[.35,.30,.20,.15],"recency_weight":.18,"overlap_penalty":.55},
"V6-D":{"windows":[20,50,100,200],"weights":[.35,.30,.20,.15],"recency_weight":.12,"overlap_penalty":1.00},
}
def load(path):
 rows=[]
 with open(path,encoding="utf-8-sig",newline="") as f:
  r=csv.reader(f); next(r,None)
  for row in r:
   if len(row)<17 or not row[0].strip().isdigit(): continue
   c=int(row[0]); d=tuple(sorted(int(x) for x in row[2:17]))
   if len(d)!=15 or len(set(d))!=15 or not all(1<=x<=25 for x in d): raise ValueError(c)
   rows.append((c,d))
 return sorted(rows)
def scores(history,cfg):
 out=[]; W=cfg["windows"]; ww=cfg["weights"]; rw=cfg["recency_weight"]
 for n in NUMS:
  fs=0
  for w,weight in zip(W,ww):
   h=history[-w:]; fs+=weight*(sum(n in d for _,d in h)+1)/(w+2)
  lag=len(history)+1
  for i in range(len(history)-1,-1,-1):
   if n in history[i][1]: lag=len(history)-i; break
  out.append((1-rw)*fs+rw/lag)
 return out
def weighted_game(weights,rng):
 pool={n:max(weights[n-1],1e-12) for n in NUMS}; out=[]
 for _ in range(K):
  total=sum(pool.values()); x=rng.random()*total; acc=0
  for n,w in list(pool.items()):
   acc+=w
   if acc>=x: out.append(n); del pool[n]; break
 return tuple(sorted(out))
def portfolio(history,rng,config="V6-C",candidates=180):
 s=scores(history,CONFIGS[config]); seen=set(); cand=[]
 while len(cand)<candidates:
  g=weighted_game(s,rng)
  if g in seen: continue
  seen.add(g); cand.append((sum(math.log(s[n-1]+1e-12) for n in g),g))
 cand.sort(reverse=True,key=lambda x:x[0]); chosen=[]
 while len(chosen)<10:
  best=None; bu=-1e99
  for score,g in cand:
   if any(g==x[1] for x in chosen): continue
   overlap=sum(len(set(g)&set(x[1])) for x in chosen)
   u=score-CONFIGS[config]["overlap_penalty"]*overlap
   if u>bu: bu=u; best=(score,g)
  chosen.append(best)
 return [g for _,g in chosen]
def evaluate(rows,start,end,config,seed):
 by={c:d for c,d in rows}; rng=random.Random(seed); vals=[]
 for c in range(start,end+1):
  hist=[x for x in rows if x[0]<c]; target=set(by[c])
  vals.append(max(len(set(g)&target) for g in portfolio(hist,rng,config)))
 return vals
def metrics(v):
 return {"contests":len(v),"mean_best":round(sum(v)/len(v),6),
 "13_plus":sum(x>=13 for x in v),"14_plus":sum(x>=14 for x in v),
 "15":sum(x>=15 for x in v),"12_plus":sum(x>=12 for x in v),
 "11_plus":sum(x>=11 for x in v),"max":max(v)}
def main():
 p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--out",default="results/v6")
 p.add_argument("--validation-start",type=int,default=2275); p.add_argument("--validation-end",type=int,default=3032)
 p.add_argument("--holdout-start",type=int,default=3033); p.add_argument("--holdout-end",type=int,default=3794)
 p.add_argument("--seed",type=int,default=20261002); a=p.parse_args()
 rows=load(a.csv); Path(a.out).mkdir(parents=True,exist_ok=True)
 validation={k:metrics(evaluate(rows,a.validation_start,a.validation_end,k,a.seed)) for k in CONFIGS}
 selected=max(CONFIGS,key=lambda k:(validation[k]["13_plus"],validation[k]["mean_best"]))
 holdout=metrics(evaluate(rows,a.holdout_start,a.holdout_end,selected,a.seed+1000))
 report={"validation":validation,"selected":selected,"holdout":holdout}
 Path(a.out,"v6_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 print(json.dumps(report,indent=2))
if __name__=="__main__": main()
