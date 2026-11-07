#!/usr/bin/env python3
"""Bounded V0.1 diagnosis: saved logs; optional ONE estimated fast-obstacle rerun."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import argparse,copy,csv,json,math,hashlib,subprocess
from dataclasses import asdict,replace
from collections import Counter
from sailboat_routing.navigation import run_episode,chart_for,_write_json
from sailboat_routing.planner import LocalWaypointPlanner,LocalWindEstimate
from sailboat_routing.metrics import segment_circle_clearance
from sailboat_routing.admission import load_admission
from sailboat_routing.wind_readout import RidgeWindReadout
from sailboat_routing.experiments import Budget
METHODS=('geometry_only','oracle_local','estimated_local')
SOURCE=ROOT/'runs/v0_comparison_20261002'
SCENE='fast_single_obstacle'
def read(p):return json.loads(p.read_text())
def save(p,d):_write_json(p,d)
def csvsave(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def rec(m,scene=SCENE):return read(SOURCE/(scene+'__'+m+'.json'))
def main():
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--capture-missing',action='store_true');args=a.parse_args()
 out=(ROOT/'runs'/args.output).resolve();assert out.is_relative_to(ROOT/'runs');out.mkdir(exist_ok=True)
 suite=read(SOURCE/'suite.json');scene=next(s for s in suite['comparison_scenarios'] if s['id']==SCENE);chart=chart_for(scene,suite)
 records={m:rec(m) for m in METHODS};oracle70=next(x for x in records['oracle_local']['planner_decisions'] if x['decision_time']==70)
 if args.capture_missing:
  rerun=out/'minimal_rerun';rerun.mkdir(exist_ok=False)
  admission=load_admission();model=RidgeWindReadout.load(ROOT/'runs/v0_fit_20261002/model.npz',expected_source_identity=admission['source_identity'],expected_dimension=270)
  original=LocalWaypointPlanner.plan;captured={}
  class MapProbe:
   def __init__(self,base):self.base=base;self.calls=[]
   def segment_clear(self,x,y):
    value=self.base.segment_clear(x,y);self.calls.append({'start':x,'end':y,'clear':value,'clearance':segment_circle_clearance(x,y,self.base.obstacles)});return value
   def route(self,x,y):return self.base.route(x,y)
  def logging_plan(self,visible):
   if visible.simulation_time==70:
    before=copy.deepcopy(self.__dict__);captured['input']=asdict(visible);captured['planner_before']={k:v for k,v in before.items() if k.startswith('_')}
    captured['same_state']={}
    for mode in METHODS:
     clone=copy.deepcopy(self);clone.mode=mode;probe=MapProbe(clone.static_map);clone.static_map=probe
     wind=(None if mode=='geometry_only' else LocalWindEstimate(**oracle70['input']['wind']) if mode=='oracle_local' else visible.wind)
     decision=original(clone,replace(visible,wind=wind))
     captured['same_state'][mode]={'wind':asdict(wind) if wind else None,'decision':asdict(decision),'geometry_checks':probe.calls}
    assert self.__dict__==before,'Offline rescore mutated live target manager'
   return original(self,visible)
  budget=Budget('v0_1_one_estimated_log_rerun');status='failed';LocalWaypointPlanner.plan=logging_plan
  try:
   row=run_episode(scene,suite,admission,rerun,budget,method='estimated_local',model=model)
   reproduced=read(ROOT/row['evidence']);assert reproduced['trajectory']==records['estimated_local']['trajectory'],'Rerun mismatch: STOP'
   assert reproduced['planner_decisions']==records['estimated_local']['planner_decisions'],'Decision mismatch: STOP'
   save(out/'missing_t70.json',captured);status='completed'
   save(out/'rerun_verification.json',{'method':'estimated_local','episodes':1,'full_trajectory_and_actions_equal':True,'all_original_logged_decisions_equal':True,'row':row})
  finally:LocalWaypointPlanner.plan=original;budget.finish(status)
 captured=read(out/'missing_t70.json')
 same=captured['same_state'];assert same['oracle_local']['decision']==oracle70['decision']
 assert {k:v for k,v in captured['input'].items() if k!='wind'}=={k:v for k,v in oracle70['input'].items() if k!='wind'}
 assert records['geometry_only']['trajectory'][:72]==records['oracle_local']['trajectory'][:72]
 table=[]
 for m,d in same.items():
  plan=d['decision'];best=min(plan['candidates'],key=lambda x:x['total']);current=captured['input']['current_goal_xy'];inc=next(x for x in plan['candidates'] if x['target_xy']==current)
  for x in plan['candidates']:
   table.append({'method':m,'candidate':x['target_xy'],'remaining_map_distance_w1':x['remaining_map_distance'],'local_wind_penalty_w0_3':x['local_wind_penalty'],'turn_penalty_w20':x['turn_penalty'],'change_penalty_w0_1':x['change_penalty'],'total':x['total'],'best_before_gates':x==best,'incumbent_minus_best':inc['total']-best['total'],'issued':plan['target_xy'],'reason':plan['reason'],'filter':'accepted'})
 csvsave(out/'t70_candidates.csv',table)
 stats=[]
 for scene in suite['comparison_scenarios']:
  g,e=rec('geometry_only',scene['id']),rec('estimated_local',scene['id']);assert g['trajectory']==e['trajectory']
  assert [(x['selected_at'],x['applied_at'],x['target']) for x in g['target_changes']]==[(x['selected_at'],x['applied_at'],x['target']) for x in e['target_changes']]
  gd={x['decision_time']:x for x in g['planner_decisions']}
  for ed in e['planner_decisions']:
   t=ed['decision_time'];ge=gd[t];ei,gi=ed['input'],ge['input']
   assert {k:v for k,v in ei.items() if k!='wind'}=={k:v for k,v in gi.items() if k!='wind'}
   ec,gc=ed['decision']['candidates'],ge['decision']['candidates'];assert [x['target_xy'] for x in ec]==[x['target_xy'] for x in gc]
   for x,y in zip(ec,gc):
    for key in ['remaining_map_distance','turn_penalty','change_penalty']:assert x[key]==y[key]
    assert abs(x['total']-x['local_wind_penalty']-y['total'])<1e-9
   er=sorted(range(len(ec)),key=lambda i:ec[i]['total']);gr=sorted(range(len(gc)),key=lambda i:gc[i]['total'])
   reason_e=ed['decision']['reason'];reason_g=ge['decision']['reason'];nonzero=any(x['local_wind_penalty']>0 for x in ec)
   if not ed['decision']['wind_used']:category='invalid_or_fallback'
   elif len(ec)<2:category='no_alternative'
   elif not nonzero:category='zero_wind_cost'
   elif er==gr:category='nonzero_rank_unchanged'
   elif er[0]==gr[0]:category='rank_changed_winner_unchanged'
   else:category='winner_changed_final_same'
   assert ed['decision']['target_xy']==ge['decision']['target_xy']
   stats.append({'scene':scene['id'],'time':t,'category':category,'candidate_count':len(ec),'geometry_rank':gr,'estimated_rank':er,'geometry_best':gc[gr[0]]['target_xy'],'estimated_best':ec[er[0]]['target_xy'],'geometry_reason':reason_g,'estimated_reason':reason_e,'issued':ed['decision']['target_xy'],'max_wind_penalty':max(x['local_wind_penalty'] for x in ec)})
 csvsave(out/'sampled_decisions.csv',stats)
 counts=dict(Counter(x['category'] for x in stats));per_scene={s['id']:dict(Counter(x['category'] for x in stats if x['scene']==s['id'])) for s in suite['comparison_scenarios']}
 # Safety uses original geometry metric on recorded positions; no physics advances.
 safety=[]
 for m in ('geometry_only','oracle_local'):
  d=records[m];initial=oracle70['input']['position_xy'];first=None
  for x in d['trajectory']:
   if x['time']<70:continue
   active=next((v['target'] for v in reversed(d['target_changes']) if v['applied_at']<=x['time']),x.get('target'))
   planned=segment_circle_clearance(x['raw'][:2],active,chart.obstacles)['safety_m']
   safety.append({'method':m,'time':x['time'],'x':x['raw'][0],'y':x['raw'][1],'active_target':active,'current_to_target_safety_m':planned,'previous_step_safety_m':x.get('safety_clearance_m')})
  if m=='oracle_local':
   first=next(x for x in d['trajectory'] if x.get('safety_clearance_m') is not None and x['safety_clearance_m']<=0)
   intrusion={'interval':[first['time']-1,first['time']],'record':first,'decision_chord_safety_m':segment_circle_clearance(initial,same[m]['decision']['target_xy'],chart.obstacles)['safety_m'],'application_chord_safety_m':segment_circle_clearance(d['trajectory'][71]['raw'][:2],same[m]['decision']['target_xy'],chart.obstacles)['safety_m']}
 csvsave(out/'safety_timeline.csv',safety)
 summary={'version':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'experiment_version':read(SOURCE/'provenance.json')['code_commit'],'relevant_version_diff':subprocess.check_output(['git','diff','857ff57','--','src/sailboat_routing/planner.py','src/sailboat_routing/navigation.py','src/sailboat_routing/metrics.py','configs/development_suite.json'],cwd=ROOT,text=True),'source_log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCE.glob('*__*.json'))},'sampled_decision_count':len(stats),'successful_planner_calls_excluding_initial':sum(rec('estimated_local',s['id'])['row']['steps'] for s in suite['comparison_scenarios']),'mutually_exclusive_counts':counts,'per_scene':per_scene,'actual_target_or_action_difference_estimated_geometry':0,'unlogged_decisions_not_classified':sum(rec('estimated_local',s['id'])['row']['steps'] for s in suite['comparison_scenarios'])-len(stats),'intrusion':intrusion,'t70':captured}
 # Persist the numerical representative and exact static-route rejection.
 example={m:next(x for x in rec(m,'fast_wide_channel')['planner_decisions'] if x['decision_time']==30) for m in ('geometry_only','estimated_local')}
 summary['representative_fast_wide_channel_t30']=example
 changed=[x for x in stats if x['category']=='winner_changed_final_same']
 summary['changed_winner_gate_reasons']=dict(Counter(x['estimated_reason'] for x in changed))
 summary['estimated_best_is_incumbent_among_changed']=sum(x['estimated_best']==x['issued'] for x in changed)
 d=records['oracle_local'];p0=oracle70['input']['position_xy'];target=same['oracle_local']['decision']['target_xy'];at=d['trajectory'][149]['raw'][:2]
 dx,dy=target[0]-p0[0],target[1]-p0[1]
 summary['intrusion']['distance_from_t70_target_chord_m']=abs(dx*(at[1]-p0[1])-dy*(at[0]-p0[0]))/math.hypot(dx,dy)
 try:chart.route(tuple(at),tuple(records['oracle_local']['scene']['goal']))
 except Exception as error:summary['intrusion']['static_route_exception']={'type':type(error).__name__,'message':str(error)}
 save(out/'summary.json',summary)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Circle
 fig,ax=plt.subplots(figsize=(8,5))
 for radius,alpha in [(125,.1),(55,.35)]:ax.add_patch(Circle((500,0),radius,color='gray',alpha=alpha))
 for m,color in [('geometry_only','#2563eb'),('oracle_local','#d97706')]:
  tr=[x for x in records[m]['trajectory'] if 70<=x['time']<=180];ax.plot([x['raw'][0] for x in tr],[x['raw'][1] for x in tr],color=color,label=m)
  target=same[m]['decision']['target_xy'];ax.plot([initial[0],target[0]],[initial[1],target[1]],'--',color=color,alpha=.65);ax.scatter(*target,marker='*',color=color,s=95)
 ax.scatter(*initial,color='black',s=25,label='decision t=70');ax.scatter(*intrusion['record']['raw'][:2],marker='x',color='red',s=70,label='first recorded intrusion t=149')
 ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.legend(fontsize=8);ax.grid(alpha=.2);ax.set_title('Same-state t=70 targets and actual trajectories (t=70..180)');fig.tight_layout();fig.savefig(out/'local_divergence.png',dpi=150);plt.close(fig)
 print(json.dumps({'counts':counts,'denominator':len(stats),'t70':same,'intrusion':intrusion,'rank_changed_examples':[x for x in stats if 'changed' in x['category'] and x['category']!='nonzero_rank_unchanged'][:4]},default=str))
if __name__=='__main__':main()
