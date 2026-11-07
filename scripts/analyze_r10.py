"""R10 finite paired evidence analysis, exact raw checks and reusable plotting input."""
from pathlib import Path
import json,sys,csv,math,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from sailboat_routing.metrics import segment_circle_clearance
from sailboat_routing.planner import CircleObstacle
from sailboat_routing.r7_dynamic import relative_minimum

def read(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=True))
def tracepath(folder,row):return ROOT/row['evidence'] if 'evidence' in row else folder/(row['scene_id']+'__'+row['variant'])/'trace.json'
def equal(a,b):return (a==b) or (a is None and math.isinf(b)) or abs(a-b)<1e-5

def audit(folder):
 rows=read(folder/'rows.json');manifest=read(folder.with_suffix('.json'));assert len(rows)==len(manifest['jobs'])
 assert {(x['scene_id'],x['variant']) for x in rows}=={(j['scene']['id'],j['variant']) for j in manifest['jobs']}
 out=[]
 for row in rows:
  path=tracepath(folder,row);data=read(path);tr=data['trajectory'];job=read(path.with_name('job.json'));scene=job['scene'];static=job.get('domain','static')=='static'
  assert row['complete'];assert all(x['time']==i for i,x in enumerate(tr));assert len(tr)-1==row['time_s']
  if static:spec=job['suite']['maps'][scene['map']]
  else:spec=scene.get('static',[])
  obs=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],60.) for o in spec)
  mm=math.inf;dyn=math.inf;length=0
  for i,x in enumerate(tr):
   a=np.asarray(tr[max(0,i-1)]['raw'][:2],dtype=np.float32);b=np.asarray(x['raw'][:2],dtype=np.float32)
   mm=min(mm,segment_circle_clearance(a,b,obs)['safety_m']);length+=float(np.linalg.norm(b-a)) if i else 0
   if not static and i:
    for q0,q1 in zip(tr[i-1]['targets'],x['targets']):
     assert q0['id']==q1['id'];d,f=relative_minimum(a,b,np.asarray(q0['position']),np.asarray(q1['position']));dyn=min(dyn,d-85)
  assert equal(row['min_safety_clearance_m'] if static else row['min_static_margin'],mm)
  if not static:assert equal(row['min_dynamic_margin'],dyn)
  assert abs(row['path_length_m']-length)<.002
  success=bool(np.linalg.norm(np.asarray(tr[-1]['raw'][:2])-scene['goal'])<=10 and mm>0 and dyn>0)
  assert row['success']==success
  for c in data.get('target_changes',data.get('changes',[])):assert c['applied_at']==c['selected_at']+1 and c['continuity_unchanged']
  out.append({'scene':row['scene_id'],'variant':row['variant'],'raw':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'success':success,'min_static':mm,'min_dynamic':dyn})
 write(folder/'r10_audit.json',{'passed':True,'episodes':len(rows),'records':out});return rows

def pair(rows,main,control):
 a={x['scene_id']:x for x in rows if x['variant']==main};b={x['scene_id']:x for x in rows if x['variant']==control};ids=sorted(set(a)&set(b));delta=[a[s]['time_s']-b[s]['time_s'] for s in ids if a[s]['success'] and b[s]['success']]
 return dict(main=main,control=control,n=len(ids),wins=[s for s in ids if a[s]['success'] and not b[s]['success']],losses=[s for s in ids if b[s]['success'] and not a[s]['success']],common_safe_n=len(delta),mean_delta=float(np.mean(delta)) if delta else None,median_delta=float(np.median(delta)) if delta else None,max_delta=max(delta) if delta else None)

def scientific_equal(a,b):
 return len(a)==len(b) and all(all(x.get(k)==y.get(k) for k in ['time','raw','command','physical_action','target','targets','observations']) for x,y in zip(a,b))

def same_state(run):
 out=[]
 for sid in ['r8new_mixed_pressure_2','r8new_endpoint_5','r8new_mixed_pressure_0']:
  ap=ROOT/'runs/r8_closedloop_20261005T062543Z/confirmation'/f'{sid}__sampled/trace.json';bp=run/'dynamic_development'/f'{sid}__nominal_hold/trace.json'
  a,b=read(ap),read(bp);other={x['time']:x for x in b['predictions']}
  p=next(x for x in a['predictions'] if x['time'] in other and x['selected']!=other[x['time']]['selected']);q=other[p['time']];t=p['time']
  assert scientific_equal(a['trajectory'][:t+1],b['trajectory'][:t+1])
  assert p['candidates'][0]['prediction']==q['candidates'][0]['prediction']
  out.append(dict(scene=sid,same_decision_time=t,same_history_and_nominal_prediction=True,first_physical_difference=next(i for i,(x,y) in enumerate(zip(a['trajectory'],b['trajectory'])) if x['raw'][:10]!=y['raw'][:10]),search_selected=p['selected'],hold_selected=q['selected'],search_candidates=[dict(name=x['name'],target=x['target'],margin=x['prediction']['min_margin'],cost=x['cost'],feasible=x['feasible']) for x in p['candidates']],main_row=a['row'],control_row=b['row'],main_source=str(ap.relative_to(ROOT)),control_source=str(bp.relative_to(ROOT))))
 write(run/'dynamic_same_state.json',out)

def main():
 run=Path(sys.argv[1]).resolve();allrows=[];parity=[];differences=[]
 for phase in ['static_development','dynamic_development','confirmation']:
  folder=run/phase
  if not (folder/'completion.json').exists():continue
  rows=audit(folder)
  for row in rows:row.update(phase=phase,raw=str(tracepath(folder,row).relative_to(ROOT)),cached=False)
  if phase=='static_development':
   for row in rows:
    if row['variant']!='boundary':continue
    oldpaths=list((ROOT/'runs/r6_reset_20261004T115808Z').glob('*/'+row['scene_id']+'__obstacle18_boundary120/*geometry_only.json'));assert len(oldpaths)==1
    new=read(ROOT/row['raw']);old=read(oldpaths[0]);ok=scientific_equal(new['trajectory'],old['trajectory']);assert ok;parity.append({'scene':row['scene_id'],'variant':'boundary','exact':ok})
   for phaseold in ['final','adaptation']:
    oldfolder=ROOT/'runs/r6_reset_20261004T115808Z'/phaseold
    for row in read(oldfolder/'rows.json'):
     if row['scene_id'] in {x['scene_id'] for x in rows} and row['variant'] in ['obstacle18_center120','obstacle18_none120','relay_m120','relay_m160']:
      x=dict(row,phase=phase,cached=True,raw=row['evidence']);rows.append(x)
   for a in [x for x in rows if x['variant']=='boundary']:
    atr=read(ROOT/a['raw'])['trajectory']
    for b in [x for x in rows if x['scene_id']==a['scene_id'] and x['variant'] in ['matched_center','matched_clipped']]:
     btr=read(ROOT/b['raw'])['trajectory'];index=next((i for i,(x,y) in enumerate(zip(atr,btr)) if x.get('command')!=y.get('command')),None)
     if index is not None:
      assert all(x['raw']==y['raw'] and x.get('command')==y.get('command') for x,y in zip(atr[:index],btr[:index]))
      j=read((ROOT/a['raw']).with_name('job.json'));obs=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],60.) for o in j['suite']['maps'][j['scene']['map']])
      from run_r10 import MatchedFrame
      from sailboat_routing.frames import LocalFrame
      raw=np.asarray(atr[index-1]['raw'],dtype=np.float32);fr=LocalFrame.for_leg(raw[:2],raw[12:14]);features={mode:MatchedFrame(fr,obs,mode).encode(raw)[-4:].tolist() for mode in ['boundary40','matched_center','matched_clipped']}
      differences.append({'scene':a['scene_id'],'control':b['variant'],'decision_time':index-1,'first_physical_state_difference':next((i for i,(x,y) in enumerate(zip(atr,btr)) if x['raw'][:10]!=y['raw'][:10]),None),'identical_physical_command_prefix':True,'position':raw[:2].tolist(),'features':features,'boundary_command':atr[index]['command'],'control_command':btr[index]['command'],'boundary_physical_action':atr[index]['physical_action'],'control_physical_action':btr[index]['physical_action'],'boundary_safe':a['success'],'control_safe':b['success']})
     else:differences.append({'scene':a['scene_id'],'control':b['variant'],'first_command_difference':None,'full_trace_equal':scientific_equal(atr,btr)})
  if phase=='dynamic_development':
   oldfolder=ROOT/'runs/r8_closedloop_20261005T062543Z/confirmation';oldrows=read(oldfolder/'rows.json')
   for row in list(rows):
    if row['variant'] in ['sampled','reactive']:
     old=next(x for x in oldrows if x['scene_id']==row['scene_id'] and x['variant']==row['variant']);ok=scientific_equal(read(ROOT/row['raw'])['trajectory'],read(tracepath(oldfolder,old))['trajectory']);assert ok;parity.append({'scene':row['scene_id'],'variant':row['variant'],'exact':ok})
   ids={x['scene_id'] for x in rows}
   present={(x['scene_id'],x['variant']) for x in rows}
   for old in oldrows:
    if old['scene_id'] in ids and (old['scene_id'],old['variant']) not in present:rows.append(dict(old,phase=phase,cached=True,raw=str(tracepath(oldfolder,old).relative_to(ROOT))))
  allrows.extend(rows)
 write(run/'baseline_parity.json',parity);write(run/'first_decision_differences.json',differences);write(run/'analysis_rows.json',allrows)
 comparisons=[]
 for phase in sorted({x['phase'] for x in allrows}):
  rows=[x for x in allrows if x['phase']==phase];variants={x['variant'] for x in rows};mainvar='sampled' if phase=='dynamic_development' or (phase=='confirmation' and any(x['variant']=='sampled' for x in rows)) else 'boundary'
  for v in sorted(variants-{mainvar}):comparisons.append(dict(phase=phase,**pair(rows,mainvar,v)))
 write(run/'comparisons.json',comparisons)
 fields=['phase','scene_id','variant','success','reason','time_s','min_safety_clearance_m','min_dynamic_margin','cpu_seconds','cached','raw']
 with (run/'episodes.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(allrows)
 same_state(run)
 if (run/'freeze.json').exists():
  f=read(run/'freeze.json');changed=[p for p,h in f['sources'].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h];assert not changed
  write(run/'freeze_audit.json',dict(passed=True,source_count=len(f['sources']),changed=changed,freeze_before_generation=f['epoch']<read(run/'confirmation.json')['generated_epoch']))
 print(json.dumps(comparisons,indent=2))
if __name__=='__main__':main()
