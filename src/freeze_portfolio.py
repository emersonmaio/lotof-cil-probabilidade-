"""Freeze prospective Lotofacil portfolios before the target contest result is known."""
import argparse, csv, json, random
from datetime import datetime, timezone
from pathlib import Path

from v6_probabilistic import CONFIGS as V6_CONFIGS, portfolio as v6_portfolio
from v7_1_optimized import CONFIGS as V7_CONFIGS, prefix_state, score_state, portfolio as v7_portfolio
from v8_adaptive import make_candidates, choose10

def load_rows(path):
    rows=[]
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader=csv.reader(f); next(reader,None)
        for row in reader:
            if len(row)<17 or not row[0].strip().isdigit(): continue
            contest=int(row[0]); draw=tuple(sorted(int(x) for x in row[2:17]))
            if len(draw)!=15 or len(set(draw))!=15 or any(n<1 or n>25 for n in draw):
                raise ValueError(f"Resultado inválido no concurso {contest}")
            rows.append((contest, draw, sum(1 << (n-1) for n in draw)))
    return sorted(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--target",type=int,required=True)
    p.add_argument("--out",default="results/frozen")
    p.add_argument("--seed",type=int,default=20261019)
    p.add_argument("--candidates",type=int,default=300)
    a=p.parse_args()
    rows=load_rows(a.csv)
    if not rows or rows[-1][0] >= a.target:
        raise ValueError("O histórico precisa terminar antes do concurso-alvo.")
    if rows[-1][0] != a.target-1:
        raise ValueError(f"Histórico termina em {rows[-1][0]}, mas alvo é {a.target}; verifique concursos faltantes.")
    history=[(c,d) for c,d,_ in rows]
    rng=random.Random(a.seed)
    games={}
    # V6: each configuration produces a portfolio from strictly prior history.
    for cfg in V6_CONFIGS:
        games[cfg]=[list(g) for g in v6_portfolio(history, rng, cfg, candidates=220)]
    # V7.1 and V8 states are built only from historical rows; no target result is read.
    numpref,pairpref,last=prefix_state(rows)
    i=len(rows)
    for cfg,cfg_params in V7_CONFIGS.items():
        indiv,pair=score_state(i,cfg_params,numpref,pairpref,last)
        games[cfg]=[list(item[1]) for item in v7_portfolio(indiv,pair,rng,cfg_params,candidates=220)]
    # V8 is an alternative portfolio search over the same prior-only scores.
    for cfg,cfg_params in V7_CONFIGS.items():
        indiv,pair=score_state(i,cfg_params,numpref,pairpref,last)
        candidates=make_candidates(indiv,pair,cfg_params,rng,a.candidates)
        games["V8-"+cfg]=[list(item[1]) for item in choose10(candidates,pair,cfg_params)]
    games["ALEATORIO"]=[sorted(rng.sample(range(1,26),15)) for _ in range(10)]
    record={
      "target_contest":a.target,
      "history_through":rows[-1][0],
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "commit":__import__("os").environ.get("GITHUB_SHA","local"),
      "seed":a.seed,
      "candidate_count":a.candidates,
      "rule":"All portfolios generated using contests strictly lower than target; do not regenerate after result.",
      "games":games
    }
    Path(a.out).mkdir(parents=True,exist_ok=True)
    path=Path(a.out,f"concurso_{a.target}_congelado.json")
    path.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(record,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
