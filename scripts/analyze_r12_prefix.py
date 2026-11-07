"""Reuse old logs; compare only common time/protocol prefixes, task IDs retained."""
import sys,json,csv,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'runs/r12_revision_20261006'
sources=list((ROOT/'runs/r8_closedloop_20261005T062543Z/confirmation').glob('*__sampled/trace.json'))+list((ROOT/'runs/r8_closedloop_20261005T062543Z/long').glob('*__sampled/trace.json'))+list((ROOT/'runs/r10_decision_20261005/confirmation').glob('*__sampled/trace.json'))
rows=[]
for f in sources:
 d=json.loads(f.read_text());tr=d['trajectory'];P=d['config'].get('period',15);event={e['time']:e for e in d['events']}
 for pre in d['predictions']:
  t=pre['time'];c=next(c for c in pre['candidates'] if c['name']==pre['selected']);pred=c['prediction'];k=min(P,len(pred['path'])-1,len(tr)-1-t)
  if k<1:continue
  # Before the next review (at t+P) the executed high-level protocol is unchanged.
  pp=np.array(pred['path'][:k+1]);actual=np.array([x['raw'][:2] for x in tr[t:t+k+1]]);errors=np.linalg.norm(pp-actual,axis=1)
  pm=min(pred['margins'][:k]);am=min(min([z['margin'] for z in x.get('dynamic',[])]+[x['static_margin'] if x.get('static_margin') is not None else math.inf]) for x in tr[t+1:t+k+1])
  rows.append(dict(source=str(f.relative_to(ROOT)),scene=d['scene']['id'],time=t,event=event[t]['event'],selected=c['name'],steps=k,full15=k==15,predicted_margin=pm,actual_margin=am,margin_error=am-pm,max_position_error=float(max(errors)),mean_position_error=float(np.mean(errors)),false_safe0=pm>0 and am<=0,false_safe30=pm>=30 and am<=0,guard_shortfall=pm>=30 and am<30,predicted_steps=len(pred['path'])-1,actual_remaining=len(tr)-1-t))
with (R/'prediction_windows.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={'source_tasks':len(sources),'windows':len(rows),'full15':sum(r['full15'] for r in rows),'truncated':sum(not r['full15'] for r in rows),'independence':'windows are clustered by source scene, not independent trials','protocol':'selected candidate only through next review; nominal feedback rules same, coordinates may diverge with state; later replanning tails excluded','by_event':{}}
for typ in sorted(set(r['event'] for r in rows)):
 rr=[r for r in rows if r['event']==typ];summary['by_event'][typ]={'n_windows':len(rr),'n_scenes':len(set(r['scene'] for r in rr)),'full15':sum(r['full15'] for r in rr),'max_error_m':max(r['max_position_error'] for r in rr),'median_max_error_m':float(np.median([r['max_position_error'] for r in rr])),'p95_max_error_m':float(np.percentile([r['max_position_error'] for r in rr],95)),'max_abs_margin_error_m':max(abs(r['margin_error']) for r in rr),'false_safe0':sum(r['false_safe0'] for r in rr),'false_safe30':sum(r['false_safe30'] for r in rr),'guard_shortfall':sum(r['guard_shortfall'] for r in rr)}
summary['largest_error']=max(rows,key=lambda r:r['max_position_error']);(R/'prediction_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
