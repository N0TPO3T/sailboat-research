from environment import *
from validate import clean
import argparse,traceback,shutil
D=R/'signed_20261107'
def save(name,value):(D/name).write_text(json.dumps(clean(value),indent=2))
def config(mode):
 c=copy.deepcopy(CONFIG);c['actuator_mode']=mode;return c
def response():
 results=[]
 # Includes both saturations, zero-increment hold and sign reversal.
 actions=[[1,1]]*12+[[0,0]]*5+[[-1,-1]]*22+[[0,0]]*5+[[1,1]]*5
 reference=None
 tr=Transport()
 try:
  for mode in ['original','native','signed']:
   e=MigrationEnv('original' if mode=='original' else 'yara',tr,config(mode));e.reset();rows=[];error=0;rate_error=0;prev=e.raw[8:10].astype(float)
   for a in actions:
    _,reward,_,_,i=e.step(a);actual=e.raw[8:10].astype(float);rows.append(dict(action=a,reward=reward,**i))
    if mode=='original':pass
    elif mode=='signed':
     expected=np.array(reference[len(rows)-1]['raw'][8:10]);error=max(error,float(np.max(np.abs(expected-actual))))
     rate_error=max(rate_error,float(np.max(np.maximum(np.abs(actual-prev)-np.pi/18,0))))
    prev=actual
   if mode=='original':reference=rows
   else:
    for a,b in zip(reference,rows):np.testing.assert_allclose(a['target_angles'],b['target_angles'],atol=1e-12,rtol=0)
   save('response_'+mode+'.json',dict(rows=rows,max_angle_error_deg=math.degrees(error),max_rate_excess_deg_s=math.degrees(rate_error)))
   results.append(dict(mode=mode,max_angle_error_deg=math.degrees(error),max_rate_excess_deg_s=math.degrees(rate_error)))
   e.close();print('RESPONSE',results[-1],flush=True)
  assert error<=math.radians(.05),(error,'signed angle gate')
  assert rate_error<=math.radians(.05),(rate_error,'signed rate gate')
  save('response_gate.json',dict(passed=True,angle_tolerance_deg=.05,rate_tolerance_deg_s=.05,rows=results))
 finally:tr.close()
def policy():
 assert json.loads((D/'response_gate.json').read_text())['passed']
 for mode in ['native','signed']:
  # New world per mode; identical scene/reset order and no rendering between trials.
  tr=Transport()
  try:
   for scene in CONFIG['scenes']:
    e=MigrationEnv('yara',tr,config(mode));p=ObstacleController(mode='eval');obs,_=e.reset(options=scene);p.reset(obs)
    rows=[dict(time=0,raw=e.raw.copy(),target_angles=[0,0])];switches=[];reason='time_limit';arrived=False
    try:
     for k in range(CONFIG['limit_s']):
      action=p.act(obs).action;obs,reward,_,truncated,info=e.step(action)
      rows.append(dict(action=action,reward=reward,observation=obs,**info))
      if info['collision']:reason='entity_collision';break
      if ('switch_at' not in scene or switches) and np.linalg.norm(e.raw[:2]-scene['goals'][-1])<=CONFIG['goal_radius_m']:
       arrived=True;reason='arrived' if e.min_safety>0 else 'arrived_with_buffer_violation';break
      if truncated:break
      if scene.get('switch_at')==e.t:
       before=e.raw[:12].copy();target=e.target.copy();obs=e.set_goal(scene['goals'][1],p)
       np.testing.assert_array_equal(e.raw[:12],before);np.testing.assert_array_equal(target,e.target)
       switches.append(dict(applied_at=e.t,history_count=len(e.commands)))
      if k%100==0:print('STEP',mode,scene['name'],k,flush=True)
    except Exception:reason='exception';save('error_'+mode+'_'+scene['name']+'.json',dict(error=traceback.format_exc()));raise
    finally:
     save('policy_'+mode+'_'+scene['name']+'.json',dict(mode=mode,scene=scene,reason=reason,success=arrived and e.min_safety>0,rows=rows,switches=switches))
     p.close();e.close()
    print('RESULT',mode,scene['name'],reason,e.t,flush=True)
  finally:
   tr.close()
   for n in ["bridge.log","gazebo.log","xvfb.log"]:
    if (R/"logs"/n).exists():shutil.copy2(R/"logs"/n,D/"logs"/(mode+"_"+n))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('stage',choices=['response','policy']);v=a.parse_args()
 save('config_'+v.stage+'.json',dict(base=CONFIG,modes=['native','signed'],model='same frozen ObstacleController(eval) and normalization',stage=v.stage))
 if v.stage=='response':response()
 else:policy()
