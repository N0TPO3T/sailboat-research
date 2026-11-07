import json,math,collections
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b')
for batch in ['fair_development','fair_adaptation']:
 vals=collections.defaultdict(list)
 for p in (r/'runs'/batch).glob('*.json'):
  x=json.loads(p.read_text())['result'];j=x['job'];label=(j['method'],j.get('inner'),j.get('surge_floor'),j.get('span'),j.get('orbit_radius'));vals[str(label)].append(x)
 print(batch)
 for k,vs in vals.items():print(k,len(vs),'inside',round(sum(v['inside_fraction'] for v in vs)/len(vs),4),'longest',max(v['max_outside_s'] for v in vs),'actuator',round(sum(v.get('actuator_variation_rad',0) for v in vs)/len(vs),1))
