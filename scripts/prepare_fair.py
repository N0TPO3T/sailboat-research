import json
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b');jobs=[]
for i,(wind,heading,prof,speed) in enumerate([(90,0,'stable',2),(90,180,'fast',2),(0,45,'slow',.5),(180,225,'fast',.5)]):
 for m,extra in [('center',{}),('phase',{'inner':.1}),('phase',{'inner':.2}),('phase',{'inner':.45}),('shuttle',{})]:
  jobs.append(dict(id=f'fair{i}_'+str(extra.get('inner','default')),method=m,seed=400+i,wind=wind,heading=heading,profile=prof,radius=50,speed=speed,horizon=1200,batch='fair_development',**extra))
(r/'runs/fair_development.json').write_text(json.dumps(jobs))
