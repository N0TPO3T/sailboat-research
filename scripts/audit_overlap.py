import json,datetime
from pathlib import Path
R=Path('/home/ot/Students/hs/sailboat-track-b');intervals=[]
for b in ['recovery_luff_control','recovery_luff_scale']:
 for p in (R/'runs'/b).glob('*.json'):
  x=json.loads(p.read_text())['result'];end=p.stat().st_mtime;start=end-x['wall_s'];intervals.append(dict(batch=b,file=str(p.relative_to(R)),estimated_start_utc=datetime.datetime.fromtimestamp(start,datetime.timezone.utc).isoformat(),write_mtime_utc=datetime.datetime.fromtimestamp(end,datetime.timezone.utc).isoformat(),estimated_start_epoch=start,write_epoch=end,wall_s=x['wall_s']))
a=[x for x in intervals if x['batch']=='recovery_luff_control'];b=[x for x in intervals if x['batch']=='recovery_luff_scale'];gap=min(x['estimated_start_epoch'] for x in b)-max(x['write_epoch'] for x in a)
events=sorted([(x['estimated_start_epoch'],1) for x in intervals]+[(x['write_epoch'],-1) for x in intervals]);active=peak=0;over=0
for i,(t,k) in enumerate(events):
 active+=k;peak=max(peak,active)
 if i+1<len(events) and active>4:over+=events[i+1][0]-t
out=dict(audit_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scheduling_error='Scale batch started without requiring preceding poll exit_code; predecessor was reported running on last poll.',all_sessions_exit_code=0,current_jobs='none; both agent and root checked',gpu_used=False,estimated_batch_gap_seconds=gap,estimated_overlap_seconds=max(0,-gap),estimated_peak_active_episode_intervals=peak,estimated_seconds_over_four=over,precision_limit='Start estimated as JSON filesystem mtime minus recorded wall_s; serialization/close time and process startup are not exact numerical-compute timestamps. This cannot prove precise process overlap or its absence; retain launch/poll discrepancy and interval bounds.',known_scale_pids=[942023,942028,942031,942032,942033],corrective_action='No further batch until explicit previous exit_code; all experimental runs now finished.',intervals=intervals)
(R/'docs/RESOURCE_SCHEDULING_INCIDENT.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='intervals'},indent=2))
