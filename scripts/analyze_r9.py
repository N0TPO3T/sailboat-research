"""R9 offline paired summaries; never advances physics."""
import json,sys,csv
from pathlib import Path
import numpy as np
R=Path(sys.argv[1]).resolve();ROOT=Path(__file__).resolve().parents[1]
summary={};allrows=[];forecast=[]
for folder in sorted(R.iterdir()):
 if not folder.is_dir() or not (folder/'rows.json').exists():continue
 rows=json.loads((folder/'rows.json').read_text());pairs={}
 for row in rows:
  d=json.loads((folder/(row['scene_id']+'__'+row['variant'])/'trace.json').read_text());row=dict(row,batch=folder.name,stage_entries=sum(e['event']=='enter' for e in d['events']),stage_decisions=sum(e.get('selected','nominal')!='nominal' for e in d['events']),endpoint_events=sum(e['event']=='endpoint_unavailable' for e in d.get('goal_events',[])),source=str((folder/(row['scene_id']+'__'+row['variant'])/'trace.json').relative_to(ROOT)))
  allrows.append(row);pairs.setdefault(row['scene_id'],{})[row['variant']]=row;tr=d['trajectory']
  for pred in d.get('predictions',[]):
   t=int(pred['time']);c=next(x for x in pred['candidates'] if x['name']==pred['selected']);p=np.array(c['prediction']['path']);n=min(len(p),len(tr)-t);a=np.array([x['raw'][:2] for x in tr[t:t+n]]);error=np.linalg.norm(p[:n]-a,axis=1);end=min(15,n-1)
   am=[min(z['margin'] for z in x['dynamic']) for x in tr[t+1:t+end+1] if x['dynamic']]
   pm=c['prediction']['margins'][:end]
   forecast.append(dict(batch=folder.name,scene=row['scene_id'],variant=row['variant'],time=t,selected=pred['selected'],prefix_steps=end,error_at_prefix_end=float(error[end]),max_prefix_error=float(max(error[:end+1])),horizon_error=float(error[-1]),prefix_predicted_min=min(pm,default=None),prefix_actual_dynamic_min=min(am,default=None),forecast_valid=c['prediction'].get('valid',True),wall_seconds=pred['wall_seconds'],source=row['source']))
 variants=sorted({x['variant'] for x in rows});by={}
 for v in variants:
  a=[x for x in allrows if x['batch']==folder.name and x['variant']==v];by[v]=dict(n=len(a),safe=sum(x['success'] for x in a),arrived=sum(x['arrived'] for x in a),dynamic=sum(x['min_dynamic_margin'] is not None and x['min_dynamic_margin']<=0 for x in a),static=sum(x['min_static_margin'] is not None and x['min_static_margin']<=0 for x in a),collision=sum(x['min_entity_margin'] is not None and x['min_entity_margin']<=0 for x in a),reasons={k:sum(x['reason']==k for x in a) for k in sorted({x['reason'] for x in a})},active_episodes=sum(x['stage_entries']>0 for x in a),max_planning=max(x['max_planning_seconds'] for x in a),mean_time_all=float(np.mean([x['time_s'] for x in a])))
 comparison={}
 for v in variants:
  if v=='reactive':continue
  pp=[x for x in pairs.values() if 'reactive' in x and v in x];cc=[x for x in pp if x['reactive']['success'] and x[v]['success']];dt=[x[v]['time_s']-x['reactive']['time_s'] for x in cc]
  comparison[v]=dict(n=len(pp),gains=sum(x[v]['success'] and not x['reactive']['success'] for x in pp),losses=sum(x['reactive']['success'] and not x[v]['success'] for x in pp),common_safe=len(cc),dt_mean=float(np.mean(dt)) if dt else None,dt_median=float(np.median(dt)) if dt else None,dt_p90=float(np.quantile(dt,.9)) if dt else None,dt_p95=float(np.quantile(dt,.95)) if dt else None,dt_max=max(dt,default=None))
 summary[folder.name]=dict(complete=(folder/'completion.json').exists(),methods=by,comparisons=comparison)
(R/'analysis.json').write_text(json.dumps(summary,indent=2));(R/'prediction_execution.json').write_text(json.dumps(forecast,indent=2))
if allrows:
 with (R/'all_rows.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for x in allrows for k in x)));w.writeheader();w.writerows(allrows)
print(json.dumps(summary,indent=2))

# Timing evidence includes actual delivery and complete controller ticks.
timing={};violations=[]
for folder in sorted(R.iterdir()):
 if not (folder/'rows.json').is_file():continue
 for row in json.loads((folder/'rows.json').read_text()):
  d=json.loads((folder/(row['scene_id']+'__'+row['variant'])/'trace.json').read_text())
  key=folder.name+'/'+row['variant'];g=timing.setdefault(key,dict(walls=[],ages=[],ticks=[],application_ticks=[],statuses={},windows=[]))
  if not d['config'].get('timed') and d.get('predictions'):g['walls'].extend(z['wall_seconds'] for z in d['predictions'])
  for z in d.get('timeline',[]):
   g['walls'].append(z['measured_wall']);status=z['status'];g['statuses'][status]=g['statuses'].get(status,0)+1
   if z['reference_apply'] is not None:
    g['ages'].append(z['reference_apply']-z['observation_time'])
    if z['reference_apply']<z['plan_ready']:violations.append(dict(scene=row['scene_id'],event=z))
  for z in d.get('control_ticks',[]):
   g['ticks'].append(z['seconds'])
   if z['application']:g['application_ticks'].append(z['seconds'])
  # Only the actually selected, delivered protocol common prefix; dropped predictions excluded.
  for ev in d.get('timeline',[]):
   if ev['status'] not in ['delivered','applied','same_reference']:continue
   t=ev['observation_time'];pred=next(z for z in d['predictions'] if z['time']==t)
   c=next(z for z in pred['candidates'] if z['name']==pred['selected'])
   end=min(len(c['prediction']['path'])-1,len(d['trajectory'])-1-t)
   next_event=next((z['observation_time'] for z in d['timeline'] if z['observation_time']>t),t+end)
   end=min(end,next_event-t)
   if end<1:continue
   pp=np.array(c['prediction']['path'][:end+1]);aa=np.array([z['raw'][:2] for z in d['trajectory'][t:t+end+1]])
   g['windows'].append(dict(scene=row['scene_id'],time=t,steps=end,selected=pred['selected'],error_end=float(np.linalg.norm(pp[-1]-aa[-1])),error_max=float(max(np.linalg.norm(pp-aa,axis=1))),pred_margin=min(c['prediction']['margins'][:end]),actual_margin=min((z['margin'] for a in d['trajectory'][t+1:t+end+1] for z in a['dynamic']),default=None)))
def describe(a):
 return dict(n=len(a),p50=float(np.median(a)),p95=float(np.quantile(a,.95)),maximum=max(a),over1=sum(x>1 for x in a)) if a else dict(n=0)
output={k:dict(**{x:describe(g[x]) for x in ['walls','ages','ticks','application_ticks']},statuses=g['statuses'],windows=g['windows']) for k,g in timing.items()}
(R/'timing_analysis.json').write_text(json.dumps(output,indent=2));(R/'timing_invariants.json').write_text(json.dumps(dict(early_delivery=violations),indent=2))

# Family summaries and explicit paired scene identities.
family={};pair_ids={}
for batch in summary:
 aa=[x for x in allrows if x['batch']==batch]
 for fam in sorted({x['family'] for x in aa}):
  for v in sorted({x['variant'] for x in aa}):
   zz=[x for x in aa if x['family']==fam and x['variant']==v]
   if zz:family[batch+'/'+fam+'/'+v]=dict(n=len(zz),safe=sum(x['success'] for x in zz),penalized_mean=float(np.mean([x['time_s'] if x['success'] else 1.8*x['distance_m'] for x in zz])))
 for v in sorted({x['variant'] for x in aa}):
  gain=[];loss=[]
  for x in aa:
   if x['variant']!=v:continue
   b=next((z for z in aa if z['scene_id']==x['scene_id'] and z['variant']=='reactive'),None)
   if b:
    if x['success'] and not b['success']:gain.append(x['scene_id'])
    if b['success'] and not x['success']:loss.append(x['scene_id'])
  pair_ids[batch+'/'+v]=dict(gains=gain,losses=loss)
(R/'family_analysis.json').write_text(json.dumps(family,indent=2));(R/'paired_identities.json').write_text(json.dumps(pair_ids,indent=2))
