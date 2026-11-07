import json,math
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b');o=json.loads((r/'runs/confirmation/confirmation_12_center__center.json').read_text());check=[]
for p in sorted((r/'runs/recovery_diagnosis').glob('*.json')):
 z=json.loads(p.read_text());assert all(a==b for a,b in zip(z['trace'][:100],o['trace'][:100]));assert z['trace'][100]['raw']==o['trace'][100]['raw'];check.append(p.name)
 if 'backwind' in p.name:
  print(p.name)
  for i in [100,110,120,130,140,150,160,170,200]:
   t=z['trace'][i];a=t['raw'];print(i,round(a[4],2),round(a[5],2),round(math.degrees(a[3]),1),round(t['d'],1))
(r/'docs/BRANCH_REPLAY_CHECK.json').write_text(json.dumps(dict(identical_before100=check,continued_raw_matches_original=all(a['raw']==b['raw'] for a,b in zip(json.loads((r/'runs/recovery_diagnosis/continue__center.json').read_text())['trace'],o['trace']))),indent=2))
