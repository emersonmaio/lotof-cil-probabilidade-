"""V8 adaptive portfolio search.

Research/backtest only. V8 keeps V7.1 temporal integrity and adds:
- larger candidate search;
- quality-aware portfolio objective emphasizing upper-tail hits while
  retaining mean/coverage;
- candidate scoring with individual + pair association;
- deterministic multi-seed evaluation.
"""
import argparse,csv,json,math,random,statistics
from pathlib import Path
from v7_1_optimized import CONFIGS,build_states,game_pair_ids,load,mask_game,metrics

V8_CANDIDATES=1000

def weighted_game(weights,rng):
    pool=[max(w,1e-12) for w in weights]; avail=list(range(1,26)); out=[]
    for _ in range(15):
        total=sum(pool); x=rng.random()*total; acc=0.0
        for i,w in enumerate(pool):
            acc+=w
            if acc>=x:
                out.append(avail.pop(i)); pool.pop(i); break
    return tuple(sorted(out))

def candidate_score(game,indiv,pair,cfg):
    base=sum(math.log(indiv[n-1]+1e-12) for n in game)
    ids=game_pair_ids(game)
    assoc=sum(pair[i] for i in ids)/len(ids)
    return base+cfg["pair_weight"]*assoc

def make_candidates(indiv,pair,cfg,rng,n):
    seen=set(); out=[]
    while len(out)<n:
        g=weighted_game(indiv,rng)
        if g in seen: continue
        seen.add(g); out.append((candidate_score(g,indiv,pair,cfg),g,mask_game(g),game_pair_ids(g)))
    return out

def choose10(candidates,pair,cfg):
    # Marginal utility: reward high intrinsic score and positive new pair coverage;
    # penalize excessive overlap. A small tail bonus favors candidates that can
    # complement already selected games rather than cloning them.
    chosen=[]; covered=set()
    for _ in range(10):
        best=None; best_u=-1e99
        for score,g,m,ids in candidates:
            if any(m==x[2] for x in chosen): continue
            overlap=sum((m&x[2]).bit_count() for x in chosen)
            novelty=sum(max(0.0,pair[i]) for i in ids if i not in covered)
            positive=sum(max(0.0,pair[i]) for i in ids)
            u=score-cfg["overlap_penalty"]*overlap+cfg["pair_novelty"]*novelty+0.03*positive
            if u>best_u: best_u=u; best=(score,g,m,ids)
        chosen.append(best); covered.update(best[3])
    return chosen

def evaluate(rows,start,end,config,seed,states,candidates_n=1000):
    by={c:m for c,_,m in rows}; rng=random.Random(seed); cfg=CONFIGS[config]; vals=[]
    for c in range(start,end+1):
        indiv,pair=states[c][config]
        games=choose10(make_candidates(indiv,pair,cfg,rng,candidates_n),pair,cfg)
        vals.append(max((g[2]&by[c]).bit_count() for g in games))
    return vals

def score_key(m):
    # Lexicographic upper-tail priority, then mean.
    return (m["15"],m["14_plus"],m["13_plus"],m["12_plus"],m["mean_best"],m["11_plus"])

def main():
    p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--out",default="results/v8")
    p.add_argument("--validation-start",type=int,default=2275); p.add_argument("--validation-end",type=int,default=3032)
    p.add_argument("--holdout-start",type=int,default=3033); p.add_argument("--holdout-end",type=int,default=3794)
    p.add_argument("--seed",type=int,default=20261002); p.add_argument("--candidates",type=int,default=1000)
    a=p.parse_args(); rows=load(a.csv); Path(a.out).mkdir(parents=True,exist_ok=True)
    states=build_states(rows,a.validation_start,a.holdout_end)
    validation={k:metrics(evaluate(rows,a.validation_start,a.validation_end,k,a.seed,states,a.candidates)) for k in CONFIGS}
    selected=max(CONFIGS,key=lambda k:score_key(validation[k]))
    holdout=metrics(evaluate(rows,a.holdout_start,a.holdout_end,selected,a.seed+1000,states,a.candidates))
    report={"engine":"V8","candidates":a.candidates,"selection_rule":"15>14+>13+>12+>mean>11+",
            "validation":validation,"selected":selected,"holdout":holdout}
    Path(a.out,"v8_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8"); print(json.dumps(report,indent=2))
if __name__=="__main__": main()
