import json,math,numpy as np
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b')
for p in sorted((r/'runs/turn_admission').glob('*.json')):
 x=json.loads(p.read_text());tr=x['trace'];j=x['result']['job'];err=np.array([abs(math.atan2(math.sin(z['raw'][3]-math.radians(j['desired'])),math.cos(z['raw'][3]-math.radians(j['desired'])))) for z in tr]);idx=np.where(err<math.radians(10))[0]
 print(p.name,'end_error',round(math.degrees(err[-1]),2),'first10deg',int(idx[0]) if len(idx) else None,'distance',round(tr[-1]['d'],1),'u',round(tr[-1]['raw'][4],2))
for p in sorted((r/'runs/pilot_corrected').glob('*.json')):
 x=json.loads(p.read_text())['result'];print(x['id'],x['method'],round(x['inside_fraction'],3),x['max_outside_s'])
