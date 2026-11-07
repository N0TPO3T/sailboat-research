import json
from pathlib import Path
from pilot import run
p=Path(__file__).resolve().parent
out=p/'runs/stability_dev2';out.mkdir(parents=True,exist_ok=False)
a=[]
for look in [4.,8.]:
 for kp in [30.,100.,200.]:
  case=dict(id=f'dev_L{look:g}_P{kp:g}',radius=10.,cruise=1.8,current=.3)
  par=dict(rate=.12,brake=.15,lookahead=look,kd=90,kp=kp,beta_tau=5.)
  r=run(case,'curvature',par,out,dt=.025);a.append(r)
  print(case['id'],r['valid_line_m'],r['elapsed_s'],r['min_hull_margin_m'],flush=True)
(out/'results.json').write_text(json.dumps(a,indent=2))
