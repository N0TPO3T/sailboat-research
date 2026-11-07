import json
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b');jobs=[]
for i,(speed,desired) in enumerate([(2,90),(2,-90),(2,180),(0,90),(-1,90)]):
 for rev in [True,False]:jobs.append(dict(id=f'turn{i}_reverse{rev}',method='heading',seed=302+i,desired=desired,wind=90,heading=0,speed=speed,horizon=180,batch='turn_admission',reverse_steering=rev))
(r/'runs/turn_admission.json').write_text(json.dumps(jobs))
