import json,sys,hashlib,math
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b');sys.path.insert(0,str(r/'scripts'))
import station
rows=[]
for when in [1,2]:
 original=station.ContinuousPhysics.step;counter=[0]
 def injected(self,command):
  out=list(original(self,command));counter[0]+=1
  if counter[0]==when:out[-1]['integration_failed']=True
  return tuple(out)
 station.ContinuousPhysics.step=injected
 j=dict(id='last' if when==2 else 'early',method='center',seed=901,horizon=2,batch='accounting_fault_check')
 x=station.worker(j);assert not x['completed'] and x['integration_failed'] and x['duration_s']==when
 rows.append(x);station.ContinuousPhysics.step=original
(r/'docs/ACCOUNTING_CHECK.json').write_text(json.dumps(rows,indent=2))
for batch in ['phase_footprint']:
 from collections import defaultdict
 d=defaultdict(list)
 for p in (r/'runs'/batch).glob('*.json'):
  x=json.loads(p.read_text())['result'];d[(x['job']['inner'],x['job']['surge_floor'])].append(x['inside_fraction'])
 print(dict(d))
for p in sorted((r/'runs/turn_admission').glob('*.json')):
 x=json.loads(p.read_text());j=x['result']['job'];tr=x['trace'];near=[z for z in tr if abs(station.wrap(z['raw'][3]-math.radians(j['desired'])))<math.radians(10)]
 if near:print(p.name,'first10',near[0]['t'],'distance',near[0]['d'])
print('SHA',hashlib.sha256((r/'scripts/station.py').read_bytes()).hexdigest())
