"""Offline truth branches and accepted-integrator-substep check. Never used online."""
import sys,json,copy,math,ast,inspect,textwrap,time
from pathlib import Path
from types import MethodType
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu,SeniorModules
configure_cpu()
import numpy as np
from sailboat_routing.continuous import ContinuousPhysics
from sailboat_routing.r8_model import CausalModel
from sailboat_routing.r8_planner import AvailabilityRelay
from sailboat_routing.r7_dynamic import observe,target_truth,relative_minimum,replay,encode
from sailboat_routing.obstacle_candidate import ObstacleController
from sailboat_routing.frames import LocalFrame
from sailboat_routing.planner import StaticMap,CircleObstacle,NoRouteError,NoLocalTargetError
from sailboat_routing.metrics import segment_circle_clearance
from sailboat_routing.navigation import bind_time_indexed_wind,_write_json
from sailboat_routing.wind_fields import SyntheticWindField
R=ROOT/'runs/r12_revision_20261006'
def parts(d):
 s=d['scene'];st=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],60.) for o in s.get('static',[]));chart=StaticMap((-2500,s['distance_m']+2500,-3000,3000),st,grid_resolution=25.)
 return s,st,chart
def frame_at(d,t):
 tr=d['trajectory'];ch=[c for c in d['changes'] if c['applied_at']<=t];k=ch[-1]['applied_at'] if ch else 0;q=ch[-1]['target'] if ch else tr[0]['target']
 return LocalFrame.for_leg(tr[k]['raw'][:2],q)
def reconstructed_base(d,t,chart):
 tr=d['trajectory'];base=AvailabilityRelay(chart,d['config']);goal=np.array(d['scene']['goal']);base.plan(np.array(tr[0]['raw'][:2]),tr[0]['raw'][3],np.zeros(2),None,goal,0,tr[0]['observations']);held=None;until=0;events={e['time']:e for e in d['events']}
 for k in range(t+1):
  if k<until:continue
  p=np.array(tr[k]['raw'][:2]);v=(p-np.array(tr[max(0,k-10)]['raw'][:2]))/max(1,min(k,10));current=frame_at(d,k).goal_world
  q=base.plan(p,tr[k]['raw'][3],v,None if held is not None else current,goal,k,tr[k]['observations'])
  if k==t:return base,np.asarray(q)
  if k in events:
   e=events[k];held=None if e['selected']=='nominal' else e['target'];until=k+d['config'].get('period',15) if held is not None else 0
 return base,None
def physics_prefix(d,t,substeps=False):
 s,st,ch=parts(d);m=SeniorModules();p=ContinuousPhysics(m,total_time_limit=1.8*s['distance_m'],world_radius_limit=s['distance_m']+3000);raw=p.reset(s['seed'],s['base_direction_degrees']);field=SyntheticWindField(s['seed']+100000,math.radians(s['base_direction_degrees']),s['profile'],horizon=int(1.8*s['distance_m'])+1);bind_time_indexed_wind(p,field);p.set_goal(d['trajectory'][0]['target'])
 if substeps:
  tree=ast.parse(textwrap.dedent(inspect.getsource(m.environment.Sailboat_nowind_last.step)));fn=tree.body[0]
  for n in fn.body:
   if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and any(isinstance(x,ast.Name) and x.id=='integration_failed' for x in n.test.values):n.test=ast.Name(id='integration_failed',ctx=ast.Load())
  fn.body[-1].value.elts[-1]=ast.Dict(keys=[ast.Constant('integration_failed')],values=[ast.Name(id='integration_failed',ctx=ast.Load())])
  class Capture(ast.NodeTransformer):
   def visit_Assign(self,n):
    if ast.unparse(n)=='self.state[0:8] = y_high':return [n,ast.parse('self._r12_samples.append((float(t), self.state[:8].copy()))').body[0]]
    return n
  tree=Capture().visit(tree);ast.fix_missing_locations(tree);ns=dict(p.env.step.__func__.__globals__);exec(compile(tree,'<r12 observation-only substep capture>','exec'),ns);p.env.step=MethodType(ns['step'],p.env)
 changes={x['applied_at']:x['target'] for x in d['changes']};maxerr=0.;sub=[]
 for k in range(t):
  before=p.raw.copy();p.env._r12_samples=[];raw,*_=p.step(np.array(d['trajectory'][k+1]['command'],np.float32));maxerr=max(maxerr,float(np.max(np.abs(raw[:12]-d['trajectory'][k+1]['raw'][:12]))))
  if substeps:
   samples=[(0.,before[:8])]+p.env._r12_samples
   for (a,x),(b,y) in zip(samples[:-1],samples[1:]):
    margin=segment_circle_clearance(x[:2],y[:2],st)['safety_m']
    for spec in s['vessels']:
     dist,f=relative_minimum(x[:2],y[:2],target_truth(spec,k+a)[0],target_truth(spec,k+b)[0]);margin=min(margin,dist-85)
    sub.append({'time':k+a,'end_time':k+b,'margin':margin})
  if k+1 in changes:p.set_goal(changes[k+1])
 assert maxerr==0.,('Prefix not reproduced',d['scene']['id'],maxerr)
 return p,maxerr,sub
def branch(d,t,candidate,base):
 s,st,ch=parts(d);tr=d['trajectory'];p,parity,_=physics_prefix(d,t);policy=ObstacleController(mode='eval');h=[np.array(x['raw'],np.float32) for x in tr[:t+1]];commands=[np.array(x['command'],np.float32) for x in tr[1:t+1]];oh=[x['observations'] for x in tr[:t+1]];frame=frame_at(d,t);current=np.array(frame.goal_world);goal=np.array(s['goal']);obs,_=replay(policy,frame,st,oh,h,commands);old=policy.act(obs).action;assert np.array_equal(old,np.array(tr[t+1]['command'],np.float32))
 path=[p.raw[:2].tolist()];margins=[];reason='horizon';refs=[];hold=candidate['hold'];target=candidate['target'];base=copy.deepcopy(base)
 for k in range(60):
  before=p.raw.copy();action=old if k==0 else policy.act(obs).action;proposed=target
  if k>0 and k>=hold:
   older=max(0,len(h)-11);v=(before[:2]-h[older][:2])/max(1,len(h)-1-older)
   try:proposed=base.plan(before[:2],before[3],v,None if hold and k==hold else tuple(current),goal,t+k,oh[-1])
   except (NoRouteError,NoLocalTargetError) as e:reason=type(e).__name__;break
  raw,_,_,truncated,info=p.step(action);h.append(raw);commands.append(action);forecast=observe(s['vessels'],t+k+1,raw[:2]);oh.append(forecast)
  margin=segment_circle_clearance(before[:2],raw[:2],st)['safety_m']
  for spec in s['vessels']:
   distance,_=relative_minimum(before[:2],raw[:2],target_truth(spec,t+k)[0],target_truth(spec,t+k+1)[0]);margin=min(margin,distance-85)
  margins.append(float(margin));path.append(raw[:2].tolist());refs.append(current.tolist())
  if info['integration_failed']:reason='integration_failed';break
  if margin<=-60:reason='entity_collision';break
  if np.linalg.norm(raw[:2]-goal)<=10:reason='arrived';break
  if truncated:reason='task_limit';break
  if np.linalg.norm(np.asarray(proposed)-current)>1e-6:
   p.set_goal(proposed);current=np.array(proposed);frame=LocalFrame.for_leg(raw[:2],proposed);obs,_=replay(policy,frame,st,oh,h,commands)
  else:obs=encode(frame,st,forecast,raw,before)
 policy.close();p.close();return {'path':path,'margins':margins,'reason':reason,'steps':len(margins),'prefix_state_max_error':parity,'references':refs}
def main():
 old=ROOT/'runs/r8_closedloop_20261005T062543Z/confirmation';new=ROOT/'runs/r10_decision_20261005/confirmation'
 specs=[(old,'r8new_mixed_pressure_2',149),(old,'r8new_mixed_pressure_4',None),(new,'r10new_endpoint_0',None),(old,'r8new_endpoint_1',341),(old,'r8new_nonconflict_0','first'),(new,'r10new_mixed_pressure_0',None)];outputs=json.loads((R/"fixed_branches.json").read_text()) if (R/"fixed_branches.json").exists() else []
 for folder,sid,t in specs:
  d=json.loads((folder/(sid+'__sampled')/'trace.json').read_text())
  if t=='first':t=d['predictions'][0]['time']
  if t is None:t=next(e['time'] for e in d['events'] if e['event']=='enter')
  pre=next(x for x in d['predictions'] if x['time']==t);s,st,ch=parts(d);base,nominal=reconstructed_base(d,t,ch);nom=pre['candidates'][0];assert np.allclose(nominal,nom['target'],atol=1e-8)
  chosen=next(x for x in pre['candidates'] if x['name']==pre['selected']);altern=nom if chosen['name']!='nominal' else dict(name='continue',target=list(frame_at(d,t).goal_world),hold=15)
  model=CausalModel();model.wind=np.array(pre['wind_estimate']);model.fitted=True;h=[np.array(x['raw'],np.float32) for x in d['trajectory'][:t+1]];acts=[np.array(x['command'],np.float32) for x in d['trajectory'][1:t+1]];oh=[x['observations'] for x in d['trajectory'][:t+1]]
  for c in [chosen,altern]:
   if any(x['scene']==sid and x['time']==t and x['candidate']==c['name'] for x in outputs):continue
   pred=model.rollout(h,acts,oh,frame_at(d,t),c['target'],np.array(d['trajectory'][t+1]['command'],np.float32),60,st,np.array(s['goal']),copy.deepcopy(base),c['hold'])
   if 'prediction' in c:assert np.array_equal(np.array(pred['path']),np.array(c['prediction']['path'])),(sid,t,c['name'],'prediction restore mismatch')
   actual=branch(d,t,c,base);k=min(len(pred['path'])-1,actual['steps']);errors=np.linalg.norm(np.array(pred['path'][:k+1])-np.array(actual['path'][:k+1]),axis=1)
   parity=None
   if c['name']==chosen['name']:
    n=min(15,actual['steps'],len(d['trajectory'])-1-t);parity=float(np.max(np.abs(np.array(actual['path'][:n+1])-np.array([x['raw'][:2] for x in d['trajectory'][t:t+n+1]]))));assert parity==0.,(sid,'selected actual prefix mismatch',parity)
   outputs.append(dict(scene=sid,time=t,candidate=c['name'],selected=c['name']==chosen['name'],prediction=pred,actual=actual,common_steps=k,max_position_error=float(max(errors)),predicted_margin=min(pred['margins'][:k]),actual_margin=min(actual['margins'][:k]),selected15s_position_parity=parity,source=str(folder/(sid+'__sampled')/'trace.json')))
   _write_json(R/'fixed_branches.json',outputs);print('branch',sid,t,c['name'],k,max(errors),flush=True)
  model.close()
 numeric=[]
 for sid in ['r8new_mixed_pressure_2','r8new_mixed_pressure_4']:
  for variant in ['reactive','sampled']:
   d=json.loads((old/(sid+'__'+variant)/'trace.json').read_text());p,e,sub=physics_prefix(d,len(d['trajectory'])-1,True);p.close();item=dict(scene=sid,variant=variant,endpoint_max_error=e,original_margin=d['row']['min_dynamic_margin'],substep_min=min(sub,key=lambda x:x['margin']),n_accepted_segments=len(sub),max_substep=max(x['end_time']-x['time'] for x in sub));numeric.append(item);_write_json(R/'substep_safety.json',numeric);print('substep',item,flush=True)
 (R/'branches_complete.json').write_text(json.dumps({'complete':True,'branches':len(outputs),'numeric_traces':len(numeric)}))
if __name__=='__main__':main()
