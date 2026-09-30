"""Run the 8+2 experiment across multiple seeds/windows and write one CSV."""
import argparse,csv,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True); p.add_argument("--out",required=True)
    p.add_argument("--start",type=int,default=500); p.add_argument("--end",type=int)
    p.add_argument("--seeds",type=int,default=20); p.add_argument("--windows",default="50,100,200")
    a=p.parse_args()
    rows=[]
    tmp=Path(a.out).with_suffix(".single.csv")
    for w in map(int,a.windows.split(",")):
        for seed in range(a.seeds):
            cmd=[sys.executable,"src/backtest_8plus2.py","--csv",a.csv,"--out",str(tmp),
                 "--start",str(a.start),"--window",str(w),"--seed",str(20260930+seed)]
            if a.end is not None: cmd += ["--end",str(a.end)]
            subprocess.run(cmd,check=True,capture_output=True,text=True)
            with tmp.open(encoding="utf-8",newline="") as f:
                for r in csv.DictReader(f):
                    r.update(window=w,seed=seed); rows.append(r)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    fields=["strategy","contests","mean_best","mean_all10","p11_plus","p12_plus","p13_plus","p14_plus","p15","window","seed"]
    with open(a.out,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    tmp.unlink(missing_ok=True)

if __name__=="__main__": main()
