"""Backtest temporal do projeto Lotofacil.
Usa somente concursos anteriores ao alvo; holdout final nao participa de selecao.
"""
import argparse, csv, random, statistics
from collections import Counter
from pathlib import Path

NUMS=tuple(range(1,26)); K=15

def load_lotofacil(path):
    rows=[]
    with open(path,encoding="utf-8-sig",newline="") as f:
        reader=csv.reader(f)
        for row in reader:
            if row and row[0].strip().lower()=="concurso":
                break
        for row in reader:
            if len(row)<17 or not row[0].strip().isdigit():
                continue
            concurso=int(row[0])
            dezenas=tuple(sorted(int(x) for x in row[2:17]))
            if len(dezenas)!=15 or len(set(dezenas))!=15 or not all(1<=n<=25 for n in dezenas):
                raise ValueError(f"Linha invalida no concurso {concurso}")
            rows.append((concurso,dezenas))
    rows.sort()
    ids=[x[0] for x in rows]
    if ids != list(range(1,len(ids)+1)):
        raise ValueError("Concursos ausentes ou fora da sequencia esperada")
    return rows

def weighted_sample(weights,rng,k=15):
    pool=dict(weights); out=[]
    for _ in range(k):
        total=sum(max(v,0.0) for v in pool.values())
        r=rng.random()*total; acc=0.0
        for n,v in list(pool.items()):
            acc += max(v,0.0)
            if acc >= r:
                out.append(n); del pool[n]; break
    return tuple(sorted(out))

def frequency(history,w):
    c=Counter(n for d in history[-w:] for n in d)
    return {n:float(c[n]) for n in NUMS}

def recency(history,w):
    h=history[-w:]
    return {n:1.0/(next((i for i,d in enumerate(reversed(h),1) if n in d),w+1)) for n in NUMS}

def make_base(history,rng,mode,w):
    if mode=="random":
        return [tuple(sorted(rng.sample(NUMS,K))) for _ in range(8)]
    f=frequency(history,w)
    if mode=="freq":
        weights={n:f[n]+1e-9 for n in NUMS}
    else:
        q=recency(history,w); m=max(f.values()) or 1
        weights={n:0.7*f[n]/m+0.3*q[n] for n in NUMS}
    out=[]; seen=set()
    while len(out)<8:
        g=weighted_sample(weights,rng)
        if g not in seen: seen.add(g); out.append(g)
    return out

def complement(base,history,rng,kind):
    cov=Counter(n for g in base for n in g)
    if kind=="coverage":
        weights={n:1.0/(1.0+cov[n]) for n in NUMS}
    else:
        f=frequency(history,min(200,len(history))); mx=max(f.values()) or 1
        weights={n:1.0+mx-f[n] for n in NUMS}
    out=[]; seen=set(base)
    while len(out)<2:
        g=weighted_sample(weights,rng)
        if g not in seen: seen.add(g); out.append(g)
    return out

def portfolio(history,rng,name,w):
    if name=="random10":
        out=[]; seen=set()
        while len(out)<10:
            g=tuple(sorted(rng.sample(NUMS,K)))
            if g not in seen: seen.add(g); out.append(g)
        return out
    mode="freq" if name.startswith("freq") else "blend"
    kind="inverse" if name.endswith("inv2") else "coverage"
    b=make_base(history,rng,mode,w)
    return b+complement(b,history,rng,kind)

def evaluate(rows,start_contest,end_contest,strategy,w,seed):
    rng=random.Random(seed); by_id={c:d for c,d in rows}; best=[]
    for c in range(start_contest,end_contest+1):
        history=[d for cc,d in rows if cc<c]
        target=by_id[c]
        hits=[len(set(g)&set(target)) for g in portfolio(history,rng,strategy,w)]
        best.append(max(hits))
    return best

def metrics(values):
    return {
        "contests":len(values),"mean_best":round(statistics.mean(values),6),
        "median_best":statistics.median(values),"std_best":round(statistics.pstdev(values),6),
        "min_best":min(values),"max_best":max(values),
        "15":sum(v>=15 for v in values),"14_plus":sum(v>=14 for v in values),
        "13_plus":sum(v>=13 for v in values),"12_plus":sum(v>=12 for v in values),
        "11_plus":sum(v>=11 for v in values),"10_plus":sum(v>=10 for v in values)
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True); p.add_argument("--out",default="results")
    p.add_argument("--window",type=int,default=100); a=p.parse_args()
    rows=load_lotofacil(a.csv)
    last_contest=rows[-1][0]
    if last_contest < 3033:
        raise ValueError(f"Historico insuficiente para holdout: ultimo concurso {last_contest}")
    splits={"validation":(2275,3032),"holdout":(3033,last_contest)}
    strategies=["random10","freq8_cov2","blend8_cov2","freq8_inv2","blend8_inv2"]
    Path(a.out).mkdir(parents=True,exist_ok=True); all_rows=[]
    for split,(start,end) in splits.items():
        for i,name in enumerate(strategies):
            vals=evaluate(rows,start,end,name,a.window,20260930+i)
            all_rows.append({"split":split,"strategy":name,**metrics(vals)})
    with open(Path(a.out)/"comparison.csv","w",newline="",encoding="utf-8") as f:
        fields=list(all_rows[0].keys()); w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(all_rows)
    with open(Path(a.out)/"README_RESULTS.md","w",encoding="utf-8") as f:
        f.write("# Resultado do backtest\n\n")
        f.write(f"Base temporal: concursos 1-{rows[-1][0]}. Para cada alvo, somente concursos anteriores sao usados.\n\n")
        f.write("| split | estrategia | 15 | 14+ | 13+ | 12+ | 11+ | media | mediana | DP | minimo | maximo |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for r in all_rows:
            f.write(f"| {r['split']} | {r['strategy']} | {r['15']} | {r['14_plus']} | {r['13_plus']} | {r['12_plus']} | {r['11_plus']} | {r['mean_best']} | {r['median_best']} | {r['std_best']} | {r['min_best']} | {r['max_best']} |\n")
        f.write(f"\nO holdout final (3033-{rows[-1][0]}) e avaliacao fora da amostra.\n")

if __name__=="__main__":
    main()
