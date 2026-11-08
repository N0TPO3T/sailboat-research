"""Bounded checks for legacy validation and native pure-sailing task profiles."""
from environment import *
from validate import clean
import argparse,traceback,shutil

def run(profile,out):
 out=out.resolve()
 if not out.is_relative_to(R/'work'):raise ValueError('output must be inside work')
 out.mkdir(parents=True,exist_ok=True)
 if (out/'result.json').exists():raise FileExistsError('existing receipt preserved')
 path=R/('config_legacy4dof.json' if profile=='legacy' else 'config_yara_benchmark.json')
 c=json.loads(path.read_text());rows=[];passed=False;error=None;tr=None;e=None
 try:
  if profile=='legacy':
   import legacy_validate
   legacy_validate.D=out
   legacy_validate.kernel();legacy_validate.response()
   rows=json.loads((out/'response_yara.json').read_text())['rows']
   passed=json.loads((out/'response_gate.json').read_text())['passed']
  else:
   assert c['physics_mode']==c['actuator_mode']==c['sail_force_model']=='native'
   assert c['action_mode']=='native_absolute' and 'fluid_density' not in c
   tr=Transport(gazebo_args='--seed 61106');e=MigrationEnv('yara',tr,c);obs,_=e.reset()
   assert e.diag['fluid_density']==dict(air_density=1.201,waterDensity=997.,water_density=997.)
   actions=[[-1,0]]*2+[[1,1]]*7+[[1,-1]]*6+[[0,0]]*4+[[-1,0]]*4
   previous_cable=e.diag['cable_actual'];previous_target=np.zeros(2)
   for i,a in enumerate(actions):
    obs,reward,_,_,info=e.step(a);d=info['diagnostics'];expected=np.array([(a[0]+1)*np.pi/4,a[1]*np.pi/3])
    np.testing.assert_array_equal(e.target,expected)
    np.testing.assert_allclose(info["reward_action_delta"],expected-previous_target,rtol=0,atol=1e-12)
    previous_target=expected.copy()
    np.testing.assert_allclose([d['cable_command'],d['rudder_command']],expected,rtol=0,atol=1e-12)
    assert obs.shape==(18,) and np.isfinite(obs).all()
    assert d['physics_mode']==d['actuator_mode']==d['sail_force_model']=='native'
    assert not d['body_static'] and not d['body_kinematic']
    assert d['motor_command']==d['motor_applied_thrust']==0 and not d['motor_plugin_present']
    assert abs(d['dt']-1)<1e-8
    assert abs(d['cable_actual']-previous_cable)<=.5+1e-8
    previous_cable=d['cable_actual']
    if i in [8,14,18,22]:
     assert abs(d['raw'][9]-expected[1])<math.radians(1),(i,d['raw'][9],expected[1])
     assert abs(d['cable_actual']-expected[0])<=.005+1e-8
    rows.append(dict(action=a,reward=reward,observation=obs,**info))
   before=e.raw[:12].copy();obs=e.set_goal([500,80]);np.testing.assert_array_equal(e.raw[:12],before)
   obs,_=e.reset();assert len(e.history)==1 and not e.commands and not np.any(e.target)
   np.testing.assert_allclose(e.raw[:10],c['initial'][:10],rtol=0,atol=2e-5)
   passed=True
 except Exception:
  error=traceback.format_exc();raise
 finally:
  if e is not None:e.close()
  if tr is not None:tr.close()
  (out/'result.json').write_text(json.dumps(clean(dict(passed=passed,profile=profile,config=c,rows=rows,error=error,training=False,paper_reproduction=False)),indent=2))
  for n in ['bridge.log','gazebo.log','xvfb.log']:
   if (R/'logs'/n).exists():shutil.copy2(R/'logs'/n,out/n)
 print(json.dumps(dict(profile=profile,passed=passed,steps=len(rows))),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('profile',choices=['legacy','yara']);a.add_argument('--output',required=True,type=Path);args=a.parse_args();run(args.profile,args.output)
