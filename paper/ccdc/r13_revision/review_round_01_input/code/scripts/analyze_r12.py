import sys,json,csv,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'runs/r12_revision_20261006';old=ROOT/'runs/r8_closedloop_20261005T062543Z/confirmation'
def pct(xs):
 return {'n':len(xs),'mean':float(np.mean(xs)) if xs else None,'median':float(np.median(xs)) if xs else None,'p90':float(np.percentile(xs,90)) if xs else None,'max':max(xs) if xs else None,'min':min(xs) if xs else None}
def augment(f,stage):
 d=json.loads(f.read_text());row=dict(d['row']);row.update(stage=stage,source=str(f.relative_to(ROOT)),predictions=len(d['predictions']),non_nominal_selections=sum(e.get('selected')!='nominal' for e in d['events'] if 'selected' in e),fallbacks=sum(e.get('all_predicted_infeasible',False) for e in d['events']))
 row['failure_type']='safe' if row['success'] else 'buffer_incursion' if min(row['min_dynamic_margin'],row['min_static_margin'] if row['min_static_margin'] is not None else math.inf)<=0 else row['reason']
 return row
summary={};allrows=[]
for stage in ['development','guard','confirmation']:
 folder=R/stage
 rows=[augment(f,stage) for f in folder.glob('*/trace.json')]
 if stage=='guard':
  ids=json.loads((R/'guard.json').read_text())['scene_ids']
  for sid in ids:
   for v,label in [('sampled','guard30'),('reactive','reactive')]:
    x=augment(old/(sid+'__'+v)/'trace.json',stage);x.update(variant=label,reused=True);rows.append(x)
 if not rows:continue
 by={}
 baseline={r['scene_id']:r for r in rows if r['variant']=='reactive'}
 for variant in sorted(set(r['variant'] for r in rows)):
  rr=[r for r in rows if r['variant']==variant];pairs=[(r,baseline[r['scene_id']]) for r in rr if r['scene_id'] in baseline];safe=[(a,b) for a,b in pairs if a['success'] and b['success']]
  by[variant]={'tasks':len(rr),'safe':sum(r['success'] for r in rr),'failures':{reason:sum(r['failure_type']==reason for r in rr) for reason in set(r['failure_type'] for r in rr)},'rescues':sum(a['success'] and not b['success'] for a,b in pairs),'losses':sum(not a['success'] and b['success'] for a,b in pairs),'min_dynamic_margin':min(r['min_dynamic_margin'] for r in rr),'interventions':sum(r['interventions'] for r in rr),'activated_tasks':sum(r['interventions']>0 for r in rr),'fallbacks':sum(r['fallbacks'] for r in rr),'non_nominal_selections':sum(r['non_nominal_selections'] for r in rr),'cpu_total':sum(r['cpu_seconds'] for r in rr),'planning_total':sum(r['planning_seconds'] for r in rr),'common_safe_time_delta_vs_R':pct([a['time_s']-b['time_s'] for a,b in safe]),'common_safe_path_delta_vs_R':pct([a['path_length_m']-b['path_length_m'] for a,b in safe])}
 summary[stage]=by;allrows+=rows
 if stage=='confirmation':
  a={r['scene_id']:r for r in rows if r['variant']=='sampled'};b={r['scene_id']:r for r in rows if r['variant']=='simple'};both=set(a)&set(b);safe=[s for s in both if a[s]['success'] and b[s]['success']]
  summary['detailed_vs_simple']={'paired_tasks':len(both),'rescues':sum(a[s]['success'] and not b[s]['success'] for s in both),'losses':sum(not a[s]['success'] and b[s]['success'] for s in both),'common_safe_time_delta':pct([a[s]['time_s']-b[s]['time_s'] for s in safe]),'common_safe_path_delta':pct([a[s]['path_length_m']-b[s]['path_length_m'] for s in safe])}
if (R/'planning_profile.json').exists():
 rows=json.loads((R/'planning_profile.json').read_text());summary['planning_profile']={v:{'wall_seconds':pct([r['wall'] for r in rows if r['model']==v]),'cpu_seconds':pct([r['cpu'] for r in rows if r['model']==v])} for v in ['detailed','simple']}
if (R/'fixed_branches.json').exists():
 rows=json.loads((R/'fixed_branches.json').read_text());summary['fixed_protocol']={'snapshots':len(set((r['scene'],r['time']) for r in rows)),'branches':len(rows),'full60_common':sum(r['common_steps']==60 for r in rows),'max_error_m':max(r['max_position_error'] for r in rows),'max_abs_margin_error':max(abs(r['actual_margin']-r['predicted_margin']) for r in rows),'predsafe0_actualunsafe':sum(r['predicted_margin']>0 and r['actual_margin']<=0 for r in rows),'predguard30_actualunsafe':sum(r['predicted_margin']>=30 and r['actual_margin']<=0 for r in rows)}
with (R/'episodes.csv').open('w') as f:
 cols=sorted(set().union(*(r.keys() for r in allrows)));w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(allrows)
(R/'analysis.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
