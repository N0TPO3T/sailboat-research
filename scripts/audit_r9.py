"""R9 deterministic evidence checks on completed actual logs; no simulation."""
import sys,json,hashlib,math
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parents[1];R=Path(sys.argv[1]).resolve();freeze=json.loads((R/'freeze.json').read_text());errors=[];checks=[]
for name,expected in freeze['files'].items():
 if hashlib.sha256((P/name).read_bytes()).hexdigest()!=expected:errors.append('frozen file changed:'+name)
for batch in ['development2','development3','confirmation','long_confirmation','sensitivity','static_regression']:
 folder=R/batch
 if not (folder/'completion.json').exists():errors.append('incomplete:'+batch);continue
 rows=json.loads((folder/'rows.json').read_text())
 for row in rows:
  d=json.loads((folder/(row['scene_id']+'__'+row['variant'])/'trace.json').read_text());tr=d['trajectory'];evs=d.get('timeline',[]);label=batch+'/'+row['scene_id']+'/'+row['variant']
  if any(z['time']!=i for i,z in enumerate(tr)):errors.append('physical clock:'+label)
  margins=[]
  for i in range(1,len(tr)):
   for target in tr[i]['targets']:
    q1=np.array(target['position']);q0=np.array(next(q['position'] for q in tr[i-1]['targets'] if q['id']==target['id']));p0=np.array(tr[i-1]['raw'][:2]);p1=np.array(tr[i]['raw'][:2]);rr=p0-q0;dd=p1-q1-rr;fraction=float(np.clip(-rr@dd/(dd@dd),0,1)) if dd@dd>1e-12 else 0.;margin=float(np.linalg.norm(rr+fraction*dd)-85);margins.append(margin)
    logged=next(q['margin'] for q in tr[i]['dynamic'] if q['id']==target['id'])
    if abs(margin-logged)>1e-6:errors.append('synchronous safety:'+label)
  if margins and abs(min(margins)-row['min_dynamic_margin'])>1e-6:errors.append('minimum margin:'+label)
  waits=[]
  for ev in evs:
   t=ev['observation_time'];a=ev.get('reference_apply')
   if a is not None and a<ev['plan_ready']:errors.append('early result:'+label)
   if ev['status']=='applied' and not any(c['applied_at']==a for c in d['changes']):errors.append('false apply:'+label)
   stop=min(ev['delivery_boundary'],len(tr)-1)
   if any(t<c['applied_at']<=stop for c in d['changes']):errors.append('reference changed during wait:'+label)
   cmds=[z['command'] for z in tr[t+1:stop+1]]
   waits.append(dict(time=t,steps=len(cmds),distinct_actual_actions=len({tuple(z) for z in cmds})))
  ticks=d.get('control_ticks',[]);expected=len(tr)-1+(1 if row['reason'] in ['NoRouteError','NoLocalTargetError'] else 0)
  if len(ticks)!=expected:errors.append('tick coverage:'+label)
  checks.append(dict(source=label,steps=len(tr)-1,ticks=len(ticks),waits=waits,max_tick=max((z['seconds'] for z in ticks),default=0),over1=sum(z['seconds']>1 for z in ticks),accepted=sum(e['status'] in ['applied','same_reference'] for e in evs),accepted_nonnominal=sum(e['status'] in ['applied','same_reference'] and e['selected']!='nominal' for e in evs)))
(R/'final_audit.json').write_text(json.dumps(dict(errors=errors,checks=checks),indent=2));print(json.dumps(dict(errors=errors,episodes=len(checks),max_tick=max((c['max_tick'] for c in checks),default=0)),indent=2))
assert not errors
