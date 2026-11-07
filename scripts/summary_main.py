import json
from pathlib import Path
from collections import defaultdict
r=Path('/home/ot/Students/hs/sailboat-track-b');d=defaultdict(list)
for p in (r/'runs/confirmation').glob('*.json'):
 x=json.loads(p.read_text())['result'];d[(x['job']['variant'],x['job']['stratum'])].append(x)
for k,vs in sorted(d.items()):print(k,len(vs),'inside',sum(x['inside_fraction'] for x in vs)/len(vs),'worstout',max(x['max_outside_s'] for x in vs),'actuator',sum(x['actuator_variation_rad'] for x in vs)/len(vs),'done',sum(x['completed'] for x in vs))
