import json
from pathlib import Path
from pilot import run
p=Path(__file__).resolve().parent
out=p/'runs/stability_dev';out.mkdir(parents=True,exist_ok=False)
a=[]
for look in [4.,8.,12.]:
 for kd in [45.,90.]:
  case=dict(id=f'dev_L{look:g}_D{kd:g}',radius=10.,cruise=1.8,current=.3)
  par=dict(rate=.12,brake=.15,lookahead=look,kd=kd,kp=30)
  r=run(case,'curvature',par,out,dt=.025);a.append(r)
  print(case['id'],r['valid_line_m'],r['elapsed_s'],r['min_hull_margin_m'],flush=True)
(out/'results.json').write_text(json.dumps(a,indent=2))
