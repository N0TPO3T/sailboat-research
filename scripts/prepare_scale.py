import json
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b')
jobs=[]
for i,(R,h,pr,start) in enumerate([(50,0,'stable',[0,0]),(50,180,'fast',[0,0]),(75,0,'fast',[0,0]),(100,-90,'slow',[150,0])]):
 for inner in [.2,.45,.7]:jobs.append(dict(id=f'scale{i}_inner{inner}',method='phase',inner=inner,seed=200+i,wind=90,heading=h,profile=pr,radius=R,start=start,horizon=1200,batch='pilot_scale'))
 for m in ['shuttle']:jobs.append(dict(id=f'scale{i}',method=m,seed=200+i,wind=90,heading=h,profile=pr,radius=R,start=start,horizon=1200,batch='pilot_scale'))
(r/'runs/pilot_scale.json').write_text(json.dumps(jobs))
