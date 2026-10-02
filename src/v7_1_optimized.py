"""V7.1 optimized backtest.

Keeps the V7 scoring equations but removes repeated historical scans:
- 25-number and 300-pair rolling counts use prefix sums.
- draws/games use 25-bit masks for hit/overlap operations.
- per (target, config) score state is cached and reused across seeds.
This is an optimization layer, not a new statistical model.
"""
import argparse, csv, json, math, random, statistics
from pathlib import Path

NUMS = tuple(range(1, 26))
K = 15
PAIRS = tuple((i, j) for i in NUMS for j in NUMS if i < j)

CONFIGS = {
    "V7-A": {"windows":[10,30,75,150], "weights":[.35,.30,.20,.15], "recency_weight":.18, "pair_weight":.15, "pair_novelty":.20, "overlap_penalty":.55},
    "V7-B": {"windows":[10,30,75,150], "weights":[.35,.30,.20,.15], "recency_weight":.18, "pair_weight":.25, "pair_novelty":.30, "overlap_penalty":.55},
    "V7-C": {"windows":[20,50,100,200], "weights":[.35,.30,.20,.15], "recency_weight":.12, "pair_weight":.20, "pair_novelty":.25, "overlap_penalty":.55},
    "V7-D": {"windows":[20,50,100,200], "weights":[.10,.20,.30,.40], "recency_weight":.08, "pair_weight":.25, "pair_novelty":.25, "overlap_penalty":.75},
}

PAIR_INDEX = {p:i for i,p in enumerate(PAIRS)}
GAME_PAIRS = {}
for mask in range(1 << 25):
    # Never populate this table; kept out intentionally because only 15-number
    # candidate masks are used and their 105 pair ids are cheap to derive.
    break

def load(path):
    rows=[]
    with open(path,encoding="utf-8-sig",newline="") as f:
        r=csv.reader(f); next(r,None)
        for row in r:
            if len(row)<17 or not row[0].strip().isdigit(): continue
            c=int(row[0]); d=tuple(sorted(int(x) for x in row[2:17]))
            if len(d)!=15 or len(set(d))!=15 or not all(1<=x<=25 for x in d): raise ValueError(c)
            mask=sum(1<<(n-1) for n in d)
            rows.append((c,d,mask))
    return sorted(rows)

def prefix_state(rows):
    n=len(rows)
    numpref=[[0]*(n+1) for _ in NUMS]
    pairpref=[[0]*(n+1) for _ in PAIRS]
    last=[[0]*(n+1) for _ in NUMS]
    for i,(_,draw,_) in enumerate(rows,1):
        s=set(draw)
        for ni,x in enumerate(NUMS):
            numpref[ni][i]=numpref[ni][i-1]+(x in s)
            last[ni][i]=i if x in s else last[ni][i-1]
        for pi,(a,b) in enumerate(PAIRS):
            pairpref[pi][i]=pairpref[pi][i-1]+(a in s and b in s)
    return numpref,pairpref,last

def score_state(i,cfg,numpref,pairpref,last):
    indiv=[0.0]*25
    for ni,n in enumerate(NUMS):
        fs=0.0
        for w,weight in zip(cfg["windows"],cfg["weights"]):
            lo=max(0,i-w)
            count=numpref[ni][i]-numpref[ni][lo]
            fs += weight*(count+1)/(w+2)
        lag=(i-last[ni][i]) if last[ni][i] else i+1
        indiv[ni]=(1-cfg["recency_weight"])*fs + cfg["recency_weight"]/lag
    pair=[0.0]*300
    for pi,(a,b) in enumerate(PAIRS):
        value=0.0
        for w,weight in zip(cfg["windows"],cfg["weights"]):
            lo=max(0,i-w)
            cij=pairpref[pi][i]-pairpref[pi][lo]
            cai=numpref[a-1][i]-numpref[a-1][lo]
            cbj=numpref[b-1][i]-numpref[b-1][lo]
            pi1=(cai+1)/(w+2); pj1=(cbj+1)/(w+2); pij=(cij+1)/(w+1)
            pmi=math.log(max(pij/max(pi1*pj1,1e-12),1e-12))
            shrink=math.sqrt(w/(w+50.0))
            value += weight*max(-1.0,min(1.0,pmi*shrink))
        pair[pi]=value
    return indiv,pair

def weighted_game(weights,rng):
    pool=[max(w,1e-12) for w in weights]
    available=list(NUMS); out=[]
    for _ in range(K):
        total=sum(pool); x=rng.random()*total; acc=0.0
        for idx,w in enumerate(pool):
            acc+=w
            if acc>=x:
                out.append(available.pop(idx)); pool.pop(idx); break
    return tuple(sorted(out))

def mask_game(game):
    m=0
    for n in game: m |= 1<<(n-1)
    return m

def game_pair_ids(game):
    return [PAIR_INDEX[(a,b)] for ix,a in enumerate(game) for b in game[ix+1:]]

def game_score(game,indiv,pair,cfg):
    base=sum(math.log(indiv[n-1]+1e-12) for n in game)
    ids=game_pair_ids(game)
    pair_term=sum(pair[i] for i in ids)/len(ids)
    return base+cfg["pair_weight"]*pair_term

def portfolio(indiv,pair,rng,cfg,candidates=220):
    seen=set(); cand=[]
    while len(cand)<candidates:
        g=weighted_game(indiv,rng)
        if g in seen: continue
        seen.add(g)
        cand.append((game_score(g,indiv,pair,cfg),g,mask_game(g)))
    chosen=[]; covered=set()
    while len(chosen)<10:
        best=None; best_u=-1e99
        for score,g,gm in cand:
            if any(gm==x[2] for x in chosen): continue
            overlap=sum((gm & x[2]).bit_count() for x in chosen)
            novelty=0.0
            for pid in game_pair_ids(g):
                if pid not in covered and pair[pid]>0: novelty+=pair[pid]
            utility=score-cfg["overlap_penalty"]*overlap+cfg["pair_novelty"]*novelty
            if utility>best_u: best_u=utility; best=(score,g,gm)
        chosen.append(best)
        covered.update(game_pair_ids(best[1]))
    return chosen

def build_states(rows,start,end):
    numpref,pairpref,last=prefix_state(rows)
    idx={c:i for i,(c,_,_) in enumerate(rows)}
    states={}
    for c in range(start,end+1):
        if c not in idx: raise ValueError(f"Contest {c} not found")
        i=idx[c]
        states[c]={k:score_state(i,cfg,numpref,pairpref,last) for k,cfg in CONFIGS.items()}
    return states

def evaluate(rows,start,end,config,seed,states,candidates=220):
    by={c:mask for c,_,mask in rows}; rng=random.Random(seed); vals=[]
    cfg=CONFIGS[config]
    for c in range(start,end+1):
        indiv,pair=states[c][config]
        selected=portfolio(indiv,pair,rng,cfg,candidates)
        target=by[c]
        vals.append(max((g[2]&target).bit_count() for g in selected))
    return vals

def metrics(v):
    return {"contests":len(v),"mean_best":round(sum(v)/len(v),6),"median_best":statistics.median(v),
            "std_best":round(statistics.pstdev(v),6),"11_plus":sum(x>=11 for x in v),
            "12_plus":sum(x>=12 for x in v),"13_plus":sum(x>=13 for x in v),
            "14_plus":sum(x>=14 for x in v),"15":sum(x>=15 for x in v),"max":max(v)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True); p.add_argument("--out",default="results/v7_1")
    p.add_argument("--validation-start",type=int,default=2275); p.add_argument("--validation-end",type=int,default=3032)
    p.add_argument("--holdout-start",type=int,default=3033); p.add_argument("--holdout-end",type=int,default=3794)
    p.add_argument("--seed",type=int,default=20261002); p.add_argument("--candidates",type=int,default=220)
    a=p.parse_args(); rows=load(a.csv); Path(a.out).mkdir(parents=True,exist_ok=True)
    states=build_states(rows,a.validation-start if False else a.validation_start,a.holdout_end)
    validation={k:metrics(evaluate(rows,a.validation_start,a.validation_end,k,a.seed,states,a.candidates)) for k in CONFIGS}
    selected=max(CONFIGS,key=lambda k:(validation[k]["13_plus"],validation[k]["mean_best"]))
    holdout=metrics(evaluate(rows,a.holdout_start,a.holdout_end,selected,a.seed+1000,states,a.candidates))
    report={"engine":"V7.1","candidates":a.candidates,"validation":validation,"selected":selected,"holdout":holdout}
    Path(a.out,"v7_1_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
