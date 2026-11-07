import json,math
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b')
for p in (r/'runs/calibration_signfix').glob('*.json'):
 x=json.loads(p.read_text());a=x['trace'][-1];print(p.name,'end_heading',math.degrees(a['raw'][3]),'speed',a['raw'][4],'heel',math.degrees(a['raw'][2]))
jobs=[dict(id='dev'+str(i),method=m,seed=100+i,wind=w,heading=h,profile=pr,radius=100,horizon=1200,batch='pilot_station') for i,(w,h,pr) in enumerate([(90,0,'stable'),(90,180,'slow'),(0,90,'fast'),(180,-90,'fast')]) for m in ['phase','phase_adaptive','orbit','shuttle']]
(r/'runs/pilot_station.json').write_text(json.dumps(jobs))
