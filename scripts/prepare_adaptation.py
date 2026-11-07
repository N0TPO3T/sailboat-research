import json
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b');jobs=[]
for i,(wind,heading,prof,speed) in enumerate([(90,0,'stable',2),(90,180,'fast',2),(0,45,'slow',.5),(180,225,'fast',.5)]):
 for m,extra,label in [('phase',{'inner':.2,'surge_floor':.5},'floor05'),('phase',{'inner':.45,'surge_floor':.5},'inner45floor05'),('phase',{'inner':.2,'surge_floor':1.},'floor1'),('orbit',{'orbit_radius':.2},'small'),('shuttle',{'span':.2},'span02'),('shuttle',{'span':.5},'span05'),('center_no_tack',{},'no_tack')]:
  jobs.append(dict(id=f'adapt{i}_'+label,method=m,seed=400+i,wind=wind,heading=heading,profile=prof,radius=50,speed=speed,horizon=1200,batch='fair_adaptation',**extra))
(r/'runs/fair_adaptation.json').write_text(json.dumps(jobs))
