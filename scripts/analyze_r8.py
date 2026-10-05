"""Offline R8 summaries; no physical rollout or method mutation."""
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
   forecast.append(dict(batch=folder.name,scene=row['scene_id'],variant=row['variant'],time=t,selected=pred['selected'],prefix_steps=end,error_15=float(error[end]),max_prefix_error=float(max(error[:end+1])),horizon_error=float(error[-1]),prefix_predicted_min=min(pm,default=None),prefix_actual_dynamic_min=min(am,default=None),forecast_valid=c['prediction'].get('valid',True),wall_seconds=pred['wall_seconds'],source=row['source']))
 variants=sorted({x['variant'] for x in rows});by={}
 for v in variants:
  a=[x for x in allrows if x['batch']==folder.name and x['variant']==v];by[v]=dict(n=len(a),safe=sum(x['success'] for x in a),arrived=sum(x['arrived'] for x in a),dynamic=sum(x['min_dynamic_margin'] is not None and x['min_dynamic_margin']<=0 for x in a),static=sum(x['min_static_margin'] is not None and x['min_static_margin']<=0 for x in a),collision=sum(x['min_entity_margin'] is not None and x['min_entity_margin']<=0 for x in a),reasons={k:sum(x['reason']==k for x in a) for k in sorted({x['reason'] for x in a})},active_episodes=sum(x['stage_entries']>0 for x in a),max_planning=max(x['max_planning_seconds'] for x in a),mean_time_all=float(np.mean([x['time_s'] for x in a])))
 comparison={}
 for v in variants:
  if v=='reactive':continue
  pp=[x for x in pairs.values() if 'reactive' in x and v in x];cc=[x for x in pp if x['reactive']['success'] and x[v]['success']];dt=[x[v]['time_s']-x['reactive']['time_s'] for x in cc]
  comparison[v]=dict(n=len(pp),gains=sum(x[v]['success'] and not x['reactive']['success'] for x in pp),losses=sum(x['reactive']['success'] and not x[v]['success'] for x in pp),common_safe=len(cc),dt_mean=float(np.mean(dt)) if dt else None,dt_median=float(np.median(dt)) if dt else None,dt_p90=float(np.quantile(dt,.9)) if dt else None,dt_max=max(dt,default=None))
 summary[folder.name]=dict(complete=(folder/'completion.json').exists(),methods=by,comparisons=comparison)
(R/'analysis.json').write_text(json.dumps(summary,indent=2));(R/'prediction_execution.json').write_text(json.dumps(forecast,indent=2))
if allrows:
 with (R/'all_rows.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for x in allrows for k in x)));w.writeheader();w.writerows(allrows)
print(json.dumps(summary,indent=2))
