#!/usr/bin/env python3
"""Fixed V0.2 experiment: check, gated 6+18 runs, saved-data analysis. No search."""
from pathlib import Path
import sys,time
PROCESS_STARTED=time.time()
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import argparse,copy,csv,json,hashlib,subprocess,signal,os
from dataclasses import asdict,replace
from collections import Counter
import numpy as np
from sailboat_routing.navigation import run_episode,chart_for,_write_json
from sailboat_routing.planner import PlannerConfig,PlannerInput,LocalWaypointPlanner,LocalWindEstimate,NoRouteError,NoLocalTargetError
from sailboat_routing.metrics import segment_circle_clearance,summarize_paired
from sailboat_routing.admission import file_hash,definition_hash,REQUIRED_CHECKS
from sailboat_routing.wind_readout import RidgeWindReadout
SOURCE=ROOT/'runs/v0_comparison_20261002'
METHODS=('geometry_only','oracle_local','estimated_local')
def read(p):return json.loads(p.read_text())
def save(p,x):_write_json(p,x)
def normal(x):return json.loads(json.dumps(x,default=lambda v:v.item()))
def csvwrite(p,rows):
 if not rows:return
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),extrasaction='ignore');w.writeheader();w.writerows(rows)
def source_hashes():
 return {str(p.relative_to(ROOT)):file_hash(p) for p in sorted((ROOT/'src/sailboat_routing').glob('*.py'))}
def inputs(out):
 old=read(out/'original_admission.json');assert old['schema']==2 and old['eligible_for_development']
 assert all(old['checks'].get(k) is True for k in REQUIRED_CHECKS)
 assert definition_hash(old['protocol'])==old['source_identity']['protocol_sha256']
 # Original admission stays immutable. Only the planner has an explicitly tested intervention.
 for name,expected in old['protocol']['source_files'].items():
  if name=='src/sailboat_routing/planner.py':
   blob=subprocess.check_output(['git','show','857ff57:'+name],cwd=ROOT);assert hashlib.sha256(blob).hexdigest()==expected
  else:assert file_hash(ROOT/name)==expected,name
 for x in old['evidence']:assert file_hash(ROOT/x['path'])==x['sha256']
 for kind in ('actor','normalizer'):assert file_hash(ROOT/old['protocol'][kind])==old['source_identity'][kind+'_sha256']
 modelpath=ROOT/'runs/v0_fit_20261002/model.npz';assert file_hash(modelpath)==read(SOURCE/'result.json')['model_sha256']
 model=RidgeWindReadout.load(modelpath,expected_source_identity=old['source_identity'],expected_dimension=270)
 return old,model
class Budget:
 def __init__(self,out):
  self.out=out;self.plan=read(out/'plan.json');self.used=sum(x['seconds'] for x in self.ledger())
 def ledger(self):return [json.loads(x) for x in (self.out/'process_ledger.jsonl').read_text().splitlines()] if (self.out/'process_ledger.jsonl').exists() else []
 def check(self):
  if time.time()>=self.plan['overall_deadline_epoch'] or self.used+time.time()-PROCESS_STARTED>=1800:raise TimeoutError('Shared V0.2 time budget exhausted')
 def finish(self,phase,status):
  with (self.out/'process_ledger.jsonl').open('a') as f:f.write(json.dumps({'phase':phase,'seconds':time.time()-PROCESS_STARTED,'status':status})+'\n')
def check(out,budget):
 old,model=inputs(out);suite=read(SOURCE/'suite.json')
 proc=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,env=os.environ|{'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=120)
 (out/'tests.log').write_text(proc.stdout+proc.stderr);assert proc.returncode==0,'Unit failure; see tests.log'
 saved=read(ROOT/'runs/v0_1_diagnosis_20261002/missing_t70.json');v=saved['input'];scene=next(x for x in suite['comparison_scenarios'] if x['id']=='fast_single_obstacle');chart=chart_for(scene,suite);results=[]
 for mode in METHODS:
  for margin in (0,25):
   planner=LocalWaypointPlanner(chart,PlannerConfig(**suite['planner_config'],tracking_margin_m=margin),mode)
   for k,val in saved['planner_before'].items():setattr(planner,k,tuple(np.float32(x) for x in val) if k=='_target' else val)
   wind=saved['same_state'][mode]['wind'];visible=PlannerInput(tuple(np.float32(x) for x in v['position_xy']),v['heading_rad'],tuple(np.float32(x) for x in v['current_goal_xy']),tuple(tuple(x) for x in v['route']),v['simulation_time'],LocalWindEstimate(**wind) if wind else None)
   before=copy.deepcopy(planner.__dict__);result=copy.deepcopy(planner).plan(visible);assert planner.__dict__==before
   result=normal(asdict(result))
   if margin==0:assert result==saved['same_state'][mode]['decision'],('Same-state baseline mismatch',mode,result)
   targets=[x['target_xy'] for x in result['candidates']]
   a=[418.61138916015625,-235.0211181640625];b=[596.1262817382812,-186.45217895507812]
   assert a in targets
   if margin==25:assert b not in targets
   results.append({'method':mode,'margin':margin,'input':normal(asdict(visible)),'decision':result})
 save(out/'same_state_t70.json',results)
 save(out/'validation.json',{'passed':True,'source_hashes':source_hashes(),'script_sha256':file_hash(Path(__file__)),'tests_log':'tests.log','same_state':'same_state_t70.json','feature_identity':old['source_identity'],'note':'Original admission is retained for frozen encoder identity; this receipt validates the planner-only intervention, not universal success.'})
 print('Validation and same-state checks passed',flush=True)
def launch(out,scene,suite,method,margin,old,model,budget,stage):
 launches=read(out/'launches.json') if (out/'launches.json').exists() else []
 key=f"{scene['id']}__{method}__m{margin}"
 assert not any(x['id']==key for x in launches),'Never relaunch an existing episode automatically'
 assert len(launches)<24,'Formal episode limit'
 budget.check();folder=out/stage/key;folder.mkdir(parents=True,exist_ok=False)
 launches.append({'id':key,'started_epoch':time.time(),'stage':stage,'status':'started'});save(out/'launches.json',launches)
 config=copy.deepcopy(suite);config['planner_config']['tracking_margin_m']=margin;save(folder/'actual_suite.json',config)
 original=LocalWaypointPlanner.plan;events=[];counts=Counter();held_below=0
 def logged(self,visible):
  nonlocal held_below
  shadow=copy.deepcopy(self);shadow.config=replace(shadow.config,tracking_margin_m=0)
  try:base=original(shadow,visible) if margin else None
  except (NoRouteError,NoLocalTargetError):base=None
  rejected=[{'target':c.target_xy,'safety_m':segment_circle_clearance(visible.position_xy,c.target_xy,self.static_map.obstacles)['safety_m']} for c in base.candidates if segment_circle_clearance(visible.position_xy,c.target_xy,self.static_map.obstacles)['safety_m']<margin] if base else []
  try:decision=original(self,visible)
  except (NoRouteError,NoLocalTargetError) as error:
   events.append({'time':visible.simulation_time,'reason':type(error).__name__,'message':str(error),'rejected_by_margin':rejected});counts[type(error).__name__]+=1;raise
  clearance=segment_circle_clearance(visible.position_xy,decision.target_xy,self.static_map.obstacles)['safety_m']
  counts[decision.reason]+=1
  if margin and decision.target_xy==visible.current_goal_xy and clearance<margin:held_below+=1
  if rejected or decision.target_xy!=visible.current_goal_xy or visible.simulation_time%30==0:
   events.append({'time':visible.simulation_time,'position':visible.position_xy,'current':visible.current_goal_xy,'issued':decision.target_xy,'reason':decision.reason,'issued_segment_safety_m':clearance,'rejected_by_margin':rejected})
  return decision
 LocalWaypointPlanner.plan=logged
 try:
  row=run_episode(scene,config,old,folder,budget,method=method,model=model if method=='estimated_local' else None)
  row.update(margin_m=margin,stage=stage,held_below_margin_decisions=held_below)
  record=read(ROOT/row['evidence'])
  if margin==0:
   previous=read(SOURCE/(scene['id']+'__'+method+'.json'))
   row['baseline_exact_match']=(record['trajectory']==previous['trajectory'] and [(x['selected_at'],x['applied_at'],x['target']) for x in record['target_changes']]==[(x['selected_at'],x['applied_at'],x['target']) for x in previous['target_changes']])
  else:row['baseline_exact_match']=None
  save(folder/'filter_log.json',{'reason_counts':dict(counts),'held_below_margin_decisions':held_below,'events':events})
  save(folder/'row.json',row);launches[-1]['status']='completed';save(out/'launches.json',launches)
  with (out/'episodes.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  assert margin!=0 or row['baseline_exact_match'],'Baseline trajectory or targets do not reproduce; STOP'
  return row
 except Exception:
  launches[-1]['status']='failed';save(out/'launches.json',launches);raise
 finally:LocalWaypointPlanner.plan=original

def execute(out,budget):
 validation=read(out/'validation.json');assert validation['passed'] and validation['source_hashes']==source_hashes();assert validation['script_sha256']==file_hash(Path(__file__))
 old,model=inputs(out);suite=read(SOURCE/'suite.json');plan=read(out/'plan.json')
 save(out/'provenance.json',{'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_hashes':source_hashes(),'model_sha256':file_hash(ROOT/'runs/v0_fit_20261002/model.npz'),'original_feature_identity':old['source_identity'],'intervention':'candidate-only tracking_margin_m 0/25; evaluation and frozen feature pipeline unchanged','command':f'.venv/bin/python -B scripts/run_v0_2.py run --run-name {out.name}'})
 rows=[]
 for stage,names in [('main',plan['main_scenes']),('regression',plan['regression_scenes'])]:
  if stage=='regression':
   gate={'baseline_reproduced':all(x['baseline_exact_match'] for x in rows if x['margin_m']==0),'minimal_checks':True,'oracle_25_safe_arrival':all(x['success'] for x in rows if x['margin_m']==25 and x['method']=='oracle_local'),'successful_controls_remain_safe':all(x['success'] for x in rows if x['margin_m']==25 and x['method']!='oracle_local')}
   gate['continue']=all(gate.values());save(out/'main_gate.json',gate)
   with (ROOT/'docs/HANDOFF.md').open('a') as f:f.write(f"\nV0.2主实验6回合完成；继续门槛={gate['continue']}，详见runs/{out.name}/main_gate.json；本轮进程累计约{budget.used+time.time()-PROCESS_STARTED:.1f}秒。\n")
   if not gate['continue']:break
  for name in names:
   scene=next(s for s in suite['comparison_scenarios'] if s['id']==name)
   for margin in (0,25):
    for method in METHODS:rows.append(launch(out,scene,suite,method,margin,old,model,budget,stage))
 save(out/'completion.json',{'completed':True,'episodes':len(rows),'regression_run':len(rows)>6,'stop':'fixed_plan_complete' if len(rows)>6 else 'main_gate_not_met'})
 csvwrite(out/'episodes.csv',[{k:v for k,v in x.items() if k!='source_identity'} for x in rows])
 print(json.dumps(read(out/'completion.json')),flush=True)
def analyze(out,budget):
 rows=[json.loads(x) for x in (out/'episodes.jsonl').read_text().splitlines()];pairs=[]
 for name in dict.fromkeys(x['scene_id'] for x in rows):
  for mode in METHODS:
   a,b=[next(x for x in rows if x['scene_id']==name and x['method']==mode and x['margin_m']==m) for m in (0,25)]
   ta,tb=read(ROOT/a['evidence']),read(ROOT/b['evidence'])
   divergence=next((x['time'] for x,y in zip(ta['trajectory'],tb['trajectory']) if x!=y),None)
   pairs.append({'scene':name,'method':mode,'success0':a['success'],'success25':b['success'],'reason0':a['reason'],'reason25':b['reason'],'safety0':a['min_safety_clearance_m'],'safety25':b['min_safety_clearance_m'],'time0':a['time_s'],'time25':b['time_s'],'path0':a['path_length_m'],'path25':b['path_length_m'],'changes0':a['target_changes'],'changes25':b['target_changes'],'first_trace_difference':divergence})
 csvwrite(out/'paired.csv',pairs)
 summary={'pairs':pairs,'per_margin':{str(m):summarize_paired([x for x in rows if x['margin_m']==m]) for m in (0,25)},'gate':read(out/'main_gate.json'),'completion':read(out/'completion.json')}
 save(out/'summary.json',summary)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Circle
 fig,axes=plt.subplots(1,3,figsize=(13,4))
 for ax,mode in zip(axes,METHODS):
  ax.add_patch(Circle((500,0),125,color='gray',alpha=.12));ax.add_patch(Circle((500,0),55,color='gray',alpha=.4))
  for margin,color in [(0,'#2563eb'),(25,'#d97706')]:
   row=next(x for x in rows if x['scene_id']=='fast_single_obstacle' and x['method']==mode and x['margin_m']==margin);d=read(ROOT/row['evidence']);xy=np.array([x['raw'][:2] for x in d['trajectory']]);ax.plot(xy[:,0],xy[:,1],color=color,label=f'm={margin}: '+row['reason']);ax.scatter(*xy[-1],color=color,s=18)
  ax.scatter(1000,0,marker='*',color='black');ax.set_title(mode);ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('x (m)');ax.set_ylabel('y (m)');ax.grid(alpha=.2);ax.legend(fontsize=7)
 fig.suptitle('Fixed development case; actual evaluation exclusion radius = 125 m');fig.tight_layout();fig.savefig(out/'main_trajectories.png',dpi=150);plt.close(fig)
 print(json.dumps(summary),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['check','run','analyze']);p.add_argument('--run-name',required=True);args=p.parse_args();out=(ROOT/'runs'/args.run_name).resolve(strict=True);assert out.is_relative_to((ROOT/'runs').resolve());budget=Budget(out);budget.check();status='failed'
 def timeout(*unused):raise TimeoutError('Shared V0.2 deadline reached')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,max(.1,min(1800-budget.used-(time.time()-PROCESS_STARTED),budget.plan['overall_deadline_epoch']-time.time())))
 try:
  {'check':check,'run':execute,'analyze':analyze}[args.phase](out,budget);status='completed'
 except Exception as error:save(out/(args.phase+'_error.json'),{'type':type(error).__name__,'message':str(error)});raise
 finally:signal.setitimer(signal.ITIMER_REAL,0);budget.finish(args.phase,status)
if __name__=='__main__':main()
