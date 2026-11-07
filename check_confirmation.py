import json,math,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];f=json.loads((R/'docs/FREEZE.json').read_text());checks=[]
assert hashlib.sha256((R/'scripts/station.py').read_bytes()).hexdigest()==f['source_sha256']
for batch,count in [('confirmation',120),('scale_check',24)]:
 paths=sorted((R/'runs'/batch).glob('*.json'));assert len(paths)==count
 assert hashlib.sha256((R/'runs'/batch/'runner_source.py').read_bytes()).hexdigest()==f['source_sha256']
 by={}
 for p in paths:
  z=json.loads(p.read_text());x=z['result'];tr=z['trace'];j=x['job'];assert [a['t'] for a in tr]==list(range(len(tr)))
  assert all(math.isfinite(a['d']) and all(math.isfinite(v) for v in a['raw']) for a in tr)
  assert all('/sailboat-track-b/' in v for v in x['source_paths'].values())
  assert not x['completed'] or len(tr)==1201
  assert not (x['completed'] and x['integration_failed'])
  assert x['max_radius']==max(a['d'] for a in tr)
  assert abs(x['inside_fraction']-sum(a['d']<=j['radius'] for a in tr[:-1])/1200)<1e-12
  key=j['scenario'];initial=(tr[0]['raw'],tr[0]['wind'],tr[0]['wind_speed'])
  if key in by:assert by[key]==initial
  else:by[key]=initial
 checks.append(dict(batch=batch,n=count,distinct_tasks=len(by),source_hash_matches=True,paired_initial_states_identical=True,finite_states=True,all_physics_paths_isolated=True,endpoint_and_failure_accounting=True))
(R/'docs/CONFIRMATION_INTEGRITY.json').write_text(json.dumps(checks,indent=2));print(checks)
