import argparse,json,math,time,traceback,hashlib,sys
from pathlib import Path
import numpy as np
from environment import *
def clean(x):
 if isinstance(x,np.ndarray):return clean(x.tolist())
 if isinstance(x,np.generic):return clean(x.item())
 if isinstance(x,float) and not math.isfinite(x):return None
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,(tuple,list)):return [clean(v) for v in x]
 return x
def save(name,data):(R/'output'/name).write_text(json.dumps(clean(data),indent=2))
def semantic():
 from sailboat_routing.frames import LocalFrame
 from sailboat_routing.r6_controller import ObstacleFrame
 tests=[]
 def check(name,fn):fn();tests.append(name)
 raw=np.array([10,20,.1,math.pi-.01,2,-.1,.02,-.03,.4,-.2,99,99,0,0],np.float32)
 frame=LocalFrame.for_leg([10,-80],[10,420]);prev=raw.copy();prev[1]-=2
 obs=frame.encode(raw,prev)
 expected=np.array([100,0,.1,math.pi/2-.01,2,-.1,.02,-.03,.4,-.2,2,2,500,0],np.float32)
 check('rotated_14_dimensions_progress',lambda:np.testing.assert_allclose(obs,expected,atol=2e-5,rtol=0))
 obstacles=(CircleObstacle((160,20),30,10),CircleObstacle((10,120),30,10),CircleObstacle((160.001,20),30,10))
 of=ObstacleFrame(frame,obstacles,'boundary40');o=of.encode(raw,prev)
 check('18D_boundary_distance_sort_150_cutoff',lambda:np.testing.assert_allclose(o[14:],[100,-math.pi/2+.01,150,-math.pi+.01],atol=2e-5,rtol=0))
 empty=ObstacleFrame(frame,(),'boundary40').encode(raw)
 check('missing_slots_and_initial_progress_zero',lambda:np.testing.assert_array_equal(empty[[10,11,14,15,16,17]],np.zeros(6)))
 check('wrap_rotation',lambda:np.testing.assert_allclose(frame.local_to_world(frame.world_to_local([33,-55])),[33,-55],atol=1e-12,rtol=0))
 e=MigrationEnv('original');e.reset()
 degree=np.pi/180
 for a in [np.array([1.,-1.]),np.array([0.,0.]),np.array([-.001,.001])]*12:
  e.step(a)
 tests+=['action_scale_floor_accumulate_saturate_matches_actual_legacy_step']
 held=e.target.copy();e.step([0,0]);np.testing.assert_array_equal(e.target,held);tests+=['zero_increment_holds_target']
 # Reward from an actual inherited transition, recomputed by same unchanged method with pre-step flags.
 e.reset();g=e.modules.globals;before=e.raw.copy();flags=[g.one_check,g.two_check,g.three_check]
 _,reward,_,_,info=e.step([.2,-.3]);g.one_check,g.two_check,g.three_check=flags
 np.testing.assert_allclose(e.env.calculate_reward(before,False),reward,atol=1e-12,rtol=0)
 tests+=['reward_reuse_actual_transition']
 o=(CircleObstacle((0,0),30,10),)
 for y,entity,safe in [(40,10,0),(30,0,-10),(29,-1,-11)]:
  c=segment_circle_clearance([-50,y],[50,y],o);assert c==dict(entity_m=entity,safety_m=safe)
 tests+=['tangent_collision_buffer_chord_exact']
 # Recurrent replay must reproduce real uninterrupted policy state/actions.
 p=ObstacleController(mode='eval');ob,_=e.reset();p.reset(ob)
 for _ in range(4):ob,*_=e.step(p.act(ob).action)
 old=p.history();current=change_reference(p,e.frame,e.history,e.commands)[0];new=p.history()
 for k in old:np.testing.assert_allclose(old[k],new[k],atol=2e-5,rtol=0)
 p.reset(current);assert p.steps==0 and np.array_equal(p.previous_action,[0,0])
 tests+=['real_history_replay_same_frame','reset_clears_policy_memory']
 p.close();e.close();save('semantic.json',dict(passed=True,tests=tests,tolerances=dict(obs_atol=2e-5,action_atol=1e-12,clock_atol=1e-8)))
 print('SEMANTIC_PASS',len(tests),flush=True)
def response_actions(name,n=40):
 a=np.zeros((n,2))
 if name=='hold':pass
 elif name=='rudder_pos':a[0,1]=1;a[20,1]=-1
 elif name=='rudder_neg':a[0,1]=-1;a[20,1]=1
 elif name=='sail':a[0:3,0]=1;a[20:23,0]=-1
 return a
def rows_initial(e):
 return [dict(time=0,raw=e.raw.tolist(),target_angles=[0,0],action=[0,0],reward=0)]
def response(tr):
 for name in ['hold','rudder_pos','rudder_neg','sail']:
  for backend in ['original','yara']:
   e=MigrationEnv(backend,tr);e.reset();rows=rows_initial(e)
   for a in response_actions(name):
    _,r,done,trunc,info=e.step(a);rows.append(dict(action=a.tolist(),reward=r,**info))
   save('response_'+name+'_'+backend+'.json',dict(rows=rows));e.close()
   print('RESPONSE',name,backend,rows[-1]['raw'][:6],flush=True)
def direction_probe(tr):
 results={}
 for backend in ['original','yara']:
  yaw=[]
  for sign in [-1,0,1]:
   cfg=dict(CONFIG);cfg['wind']=[0,0,0];cfg['initial']=list(CONFIG['initial']);cfg['initial'][4]=2.
   e=MigrationEnv(backend,tr,cfg);e.reset();rows=rows_initial(e)
   for k in range(8):
    _,r,_,_,info=e.step([0,sign if k==0 else 0]);rows.append(dict(reward=r,**info))
   yaw.append(float(e.raw[3]));save('direction_'+backend+'_'+str(sign)+'.json',dict(rows=rows));e.close()
  assert yaw[0]<yaw[1]<yaw[2],(backend,yaw)
  results[backend]=yaw
 save('direction_gate.json',dict(passed=True,wind=[0,0,0],initial_u=2.,yaw_negative_zero_positive=results))
 print('DIRECTION_GATE_PASS',results,flush=True)

def policy(tr,resume=False):
 for scene in CONFIG['scenes']:
  for backend in ['original','yara']:
   if resume and (R/'output'/('policy_'+scene['name']+'_'+backend+'.json')).exists():
    print('PRESERVED_COMPLETED',scene['name'],backend,flush=True);continue
   e=MigrationEnv(backend,tr);p=ObstacleController(mode='eval');obs,_=e.reset(options=scene);p.reset(obs)
   rows=rows_initial(e);switches=[];reason='time_limit';final=False;start=time.monotonic()
   for k in range(CONFIG['limit_s']):
    a=p.act(obs).action;obs,reward,done,trunc,info=e.step(a)
    rows.append(dict(action=a.tolist(),reward=reward,observation=obs.tolist(),**info))
    if info['collision']:reason='entity_collision';break
    if info.get('integration_failed'):reason='integration_failed';break
    if ('switch_at' not in scene or switches) and np.linalg.norm(e.raw[:2]-scene['goals'][-1])<=CONFIG['goal_radius_m']:
     final=True;reason='arrived' if e.min_safety>0 else 'arrived_with_buffer_violation';break
    if trunc:break
    if scene.get('switch_at')==e.t:
     before=e.raw[:12].copy();targets=e.target.copy();obs=e.set_goal(scene['goals'][1],p)
     np.testing.assert_array_equal(before,e.raw[:12]);np.testing.assert_array_equal(targets,e.target)
     switches.append(dict(selected_at=e.t-1,applied_at=e.t,goal=scene['goals'][1],real_history_steps=len(e.commands)))
    if k%100==0:print('POLICY',scene['name'],backend,k,flush=True)
   result=dict(scene=scene,backend=backend,reason=reason,success=final and e.min_safety>0,rows=rows,switches=switches,wall_s=time.monotonic()-start)
   save('policy_'+scene['name']+'_'+backend+'.json',result)
   print('RESULT',scene['name'],backend,reason,'time',e.t,flush=True)
   if backend=='yara':
    trace=[np.asarray(row['raw'][:2]).tolist() for row in rows]
    receipt=tr.request('capture',xy=e.raw[:2].tolist(),trace=trace,filename='actual_'+scene['name']+'_boat.png')
    save('capture_'+scene['name']+'_boat.json',receipt)
    receipt=tr.request('capture',xy=e.raw[:2].tolist(),offset=[-2,-5,.3],look_z=-.4,trace=[],filename='actual_'+scene['name']+'_rudder.png')
    save('capture_'+scene['name']+'_rudder.json',receipt)
    # scene-wide camera includes frozen targets, obstacles and actual trace.
    receipt=tr.request('capture',xy=[250,0],offset=[-200,-300,450],trace=[],filename='actual_'+scene['name']+'_scene.png')
    save('capture_'+scene['name']+'_scene.json',receipt)
   p.close();e.close()
def smoke(tr):
 e=MigrationEnv('yara',tr);o,_=e.reset();rows=rows_initial(e)
 for a in [[0,0],[1,1],[0,0],[-1,-1]]:
  o,r,d,t,i=e.step(a);rows.append(dict(reward=r,**i))
 save('smoke.json',dict(passed=True,rows=rows));e.close();print('SMOKE_PASS',flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['semantic','smoke','response','policy','capture','all'],default='all');parser.add_argument('--resume',action='store_true');args=parser.parse_args()
 semantic()
 if args.stage!='semantic':
  tr=None
  try:
   tr=Transport()
   if args.stage in ['smoke','capture','all']:smoke(tr)
   if args.stage=='capture':
    d=json.loads((R/'output/smoke.json').read_text());xy=d['rows'][-1]['raw'][:2]
    save('capture_smoke.json',tr.request('capture',xy=xy,trace=[x['raw'][:2] for x in d['rows']],filename='actual_smoke.png'))
    save('capture_underwater.json',tr.request('capture',xy=xy,offset=[-2,-4,-.7],look_z=-.4,hide_water=True,trace=[],filename='actual_underwater.png'))
   if args.stage in ['response','all']:
    direction_probe(tr);response(tr)
   if args.stage in ['policy','all']:policy(tr,args.resume)
  except Exception:
   save('error_'+args.stage+'.json',dict(error=traceback.format_exc()));raise
  finally:
   if tr:tr.close()
