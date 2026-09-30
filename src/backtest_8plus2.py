"""Reproducible Lotofacil 8+2 backtest. No look-ahead: target draw is never used in model inputs."""
import argparse,csv,random
from collections import Counter
from pathlib import Path

N=range(1,26); K=15

def load(p):
    with open(p,encoding="utf-8",newline="") as f:
        r=csv.DictReader(f,delimiter=";"); rows=[]
        for x in r:
            d=tuple(sorted(map(int,x["dezenas"].split())))
            if len(d)!=15 or len(set(d))!=15 or not all(1<=n<=25 for n in d): raise ValueError(x)
            rows.append((int(x["concurso"]),d))
    rows.sort()
    if rows and [x[0] for x in rows]!=list(range(1,rows[-1][0]+1)): raise ValueError("missing contest")
    return rows

def weighted(w,k,rng):
    a=dict(w); out=[]
    for _ in range(k):
        t=sum(max(v,0.0) for v in a.values()); z=rng.random()*t; s=0
        for n,v in a.items():
            s+=max(v,0.0)
            if s>=z: out.append(n); del a[n]; break
    return tuple(sorted(out))

def freq(h,w):
    c=Counter(n for d in h[-w:] for n in d); return {n:float(c[n]) for n in N}

def recency(h,w):
    h=h[-w:]; out={}
    for n in N:
        lag=next((i for i,d in enumerate(reversed(h),1) if n in d),w+1)
        out[n]=1/lag
    return out

def base(h,rng,mode,w):
    if mode=="freq": s=freq(h,w)
    elif mode=="blend":
        f=freq(h,w); q=recency(h,w); m=max(f.values()) or 1
        s={n:.7*f[n]/m+.3*q[n] for n in N}
    else: s={n:1 for n in N}
    out=[]; seen=set()
    while len(out)<8:
        g=tuple(sorted(rng.sample(tuple(N),K))) if mode=="random" else weighted(s,K,rng)
        if g not in seen: seen.add(g); out.append(g)
    return out

def comp(base,h,rng,kind):
    cov=Counter(n for g in base for n in g)
    if kind=="coverage": w={n:1/(1+cov[n]) for n in N}
    elif kind=="inverse":
        f=freq(h,min(200,len(h))); m=max(f.values()) or 1; w={n:1+m-f[n] for n in N}
    else: w={n:1 for n in N}
    out=[]; seen=set(base)
    while len(out)<2:
        g=weighted(w,K,rng)
        if g not in seen: seen.add(g); out.append(g)
    return out

def random10(rng):
    out=[]; seen=set()
    while len(out)<10:
        g=tuple(sorted(rng.sample(tuple(N),K)))
        if g not in seen: seen.add(g); out.append(g)
    return out

def games(h,rng,name,w):
    if name=="random10": return random10(rng)
    mode="freq" if name.startswith("freq") else "blend"
    kind="inverse" if name.endswith("inv2") else "coverage"
    b=base(h,rng,mode,w); return b+comp(b,h,rng,kind)

def run(rows,name,start,end,seed,w):
    rng=random.Random(seed); best=[]; avg=[]; ge=Counter()
    for i in range(start,end):
        gs=games([d for _,d in rows[:i]],rng,name,w); target=rows[i][1]
        hs=[len(set(g)&set(target)) for g in gs]; b=max(hs)
        best.append(b); avg.append(sum(hs)/10)
        for k in (11,12,13,14,15): ge[k]+=b>=k
    m=len(best)
    return dict(strategy=name,contests=m,mean_best=sum(best)/m,mean_all10=sum(avg)/m,
                p11_plus=ge[11]/m,p12_plus=ge[12]/m,p13_plus=ge[13]/m,
                p14_plus=ge[14]/m,p15=ge[15]/m)

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--csv",required=True); a.add_argument("--out",required=True)
    a.add_argument("--start",type=int,default=500); a.add_argument("--end",type=int)
    a.add_argument("--window",type=int,default=100); a.add_argument("--seed",type=int,default=20260930)
    x=a.parse_args(); rows=load(x.csv); end=min(x.end or len(rows),len(rows))
    names=["random10","freq8_cov2","blend8_cov2","freq8_inv2","blend8_inv2"]
    result=[run(rows,n,x.start,end,x.seed+i,x.window) for i,n in enumerate(names)]
    Path(x.out).parent.mkdir(parents=True,exist_ok=True)
    with open(x.out,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=result[0]); w.writeheader(); w.writerows(result)
    for r in result: print(r)

if __name__=="__main__": main()
