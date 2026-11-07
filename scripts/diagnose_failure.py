import json,math
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b')
for p in sorted((r/'runs/confirmation').glob('*__center.json')):
 z=json.loads(p.read_text());x=z['result']
 if x['inside_fraction']>.5:continue
 print(p.name,x['inside_fraction'],x['job'])
 for i in [0,30,100,200,600,1200]:
  t=z['trace'][i];a=t['raw'];print(i,'d',round(t['d'],1),'psi/w/ref',*[round(math.degrees(v),1) if v is not None else None for v in [a[3],t['wind'],t['desired_heading']]],'u/v/r',a[4],a[5],a[7],'sail/rudder',*[round(math.degrees(v),1) for v in a[8:10]])
