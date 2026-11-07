import json
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b');jobs=[]
for i,(wind,heading,prof,speed) in enumerate([(90,0,'stable',2),(90,180,'fast',2),(0,45,'slow',.5),(180,225,'fast',.5)]):
 for inner,floor in [(.8,0),(1.,0),(.8,.5),(1.,.5)]:
  jobs.append(dict(id=f'proper{i}_inner{inner}_floor{floor}',method='phase',inner=inner,outer=2.,surge_floor=floor,seed=400+i,wind=wind,heading=heading,profile=prof,radius=50,speed=speed,horizon=1200,batch='phase_footprint'))
(r/'runs/phase_footprint.json').write_text(json.dumps(jobs))
