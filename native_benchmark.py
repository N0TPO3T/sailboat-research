"""Bounded native Yara acceptance; frozen actor runs remain transfer diagnostics."""
from environment import *
from validate import clean
from native6dof_policy import write
import argparse, traceback, shutil, xml.etree.ElementTree as ET

def native_state(d):
 assert d['physics_mode']==d['actuator_mode']==d['sail_force_model']=='native'
 assert not d['body_static'] and not d['body_kinematic']
 assert d['fluid_density']==dict(air_density=1.201,waterDensity=997.,water_density=997.)
 assert d['motor_command']==d['motor_applied_thrust']==0 and not d['motor_plugin_present']

def check(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=False)
 c=json.loads((R/'config_yara_transfer.json').read_text())
 checks=[];records={};tr=None;error=None
 try:
  # Full installed geometry, inertia, hydrodynamics and foil configuration.
  source=R.parent/'workspace/eboat4tr.urdf'
  installed=ET.parse(source).getroot();adapted=ET.parse(R/'boat.urdf').getroot()
  removed=json.loads((R/'removed_plugins.json').read_text())
  for g in installed.findall('gazebo'):
   for p in list(g):
    if dict(p.attrib) in removed:g.remove(p)
  def canonical(x):return (x.tag,sorted(x.attrib.items()),(x.text or '').strip(),[canonical(y) for y in x])
  assert canonical(installed)==canonical(adapted)
  assert not adapted.findall('.//plugin[@filename="libPropulsorControllerPlugin.so"]')
  records['installed_model']=dict(source=str(source),all_remaining_xml_equal=True,removed=removed,
   actuator_execution='native laws executed synchronously by step.cc; original ROS controllers removed to avoid concurrent writes',
   task_extension='18D, two actions, pure sailing, fixed wind, no waves; not paper reproduction')
  checks.append('installed_hull_inertia_and_force_parameters_unchanged')
  import validate,profile_check
  old_save=validate.save
  try:
   validate.save=lambda name,value:write(out,name,value)
   validate.semantic()
  finally:validate.save=old_save
  checks.append('shared_observation_reward_safety_history_semantics')
  profile_check.run('yara',out/'absolute')
  checks.append('native_absolute_controls_23_steps')
  tr=Transport(gazebo_args='--seed 61106')
  records['resets']=[]
  for roll,pitch,yaw in [(0.,0.,0.),(.17,.12,1.1),(-.21,-.09,-1.4)]:
   cfg=copy.deepcopy(c);cfg['initial'][2:8]=[roll,yaw,.7,.12,.04,.06]
   cfg['initial_6dof']=dict(z=.15,pitch=pitch,w=.12,q=.07)
   e=MigrationEnv('yara',tr,cfg)
   try:
    e.reset();d=e.diag;native_state(d)
    np.testing.assert_allclose([d['pose6'][2],d['pose6'][4],d['body_twist6'][2],d['body_twist6'][4]],[.15,pitch,.12,.07],rtol=0,atol=2e-5)
    records['resets'].append(d)
   finally:e.close()
  checks.append('three_nonzero_attitude_and_twist_resets')
  e=MigrationEnv('yara',tr,c);original=MigrationEnv('original',config=c)
  records['response']=[]
  try:
   e.reset();original.reset();previous_cable=0.
   actions=[[1,1]]*12+[[0,0]]*5+[[-1,-1]]*22+[[0,0]]*5+[[1,1]]*5
   for a in actions:
    old=e.target.copy();obs,reward,_,_,info=e.step(a);original.step(a);d=info['diagnostics'];native_state(d)
    np.testing.assert_array_equal(e.target,original.target)
    np.testing.assert_allclose(info['native_commands'],[abs(e.target[0]),-e.target[1]],atol=1e-12,rtol=0)
    assert abs(d['dt']-1)<1e-8 and abs(d['clock']-e.clock0-e.t)<1e-8
    assert abs(d['cable_actual']-previous_cable)<=.5+1e-8
    if a==[0,0]:np.testing.assert_array_equal(e.target,old)
    previous_cable=d['cable_actual']
    assert obs.shape==(18,) and np.isfinite(obs).all()
    records['response'].append(dict(action=a,reward=reward,observation=obs,original_raw=original.raw.copy(),**info))
   checks.append('49_step_increment_accumulation_saturation_hold_and_native_commands')
   p=ObstacleController(mode='eval');p.reset(obs)
   # Replay uses only actions and observations which actually occurred.
   e.set_goal([500,80],p)
   assert p.steps==len(e.commands)
   assert np.array_equal(p.previous_action,e.commands[-1])
   p.close();e.reset()
   assert len(e.history)==1 and not e.commands and not np.any(e.target)
   native_state(e.diag);checks.append('causal_goal_replay_and_reset')
  finally:e.close();original.close()
  records['direction']=[]
  for sign in [-1,0,1]:
   cfg=copy.deepcopy(c);cfg['wind']=[0,0,0];cfg['initial'][4]=2.
   e=MigrationEnv('yara',tr,cfg)
   try:
    e.reset();rows=[]
    for k in range(8):
     _,_,_,_,info=e.step([0,sign if k==0 else 0]);rows.append(info)
    records['direction'].append(dict(sign=sign,rows=rows))
   finally:e.close()
  yaws=[r['rows'][-1]['raw'][3] for r in records['direction']]
  assert yaws[0]<yaws[1]<yaws[2],yaws
  checks.append('rudder_world_yaw_direction')
  cfg=copy.deepcopy(c);cfg['wind']=[0,0,0];cfg['initial'][4]=3.
  e=MigrationEnv('yara',tr,cfg);records['contact']=[]
  try:
   e.reset(options=dict(name='contact_probe',goals=[[500,0]],obstacles=[dict(center_xy=[3,0],entity_radius=.4,safety_buffer=0)]))
   for k in range(5):
    _,_,_,_,info=e.step([0,0]);records['contact'].append(info)
   assert any(x['physical_contact'] for x in records['contact'])
   checks.append('actual_obstacle_contact_separate_from_unchanged_point_safety_score')
  finally:e.close()
 except Exception:
  error=traceback.format_exc();raise
 finally:
  if tr is not None:tr.close()
  write(out,'result.json',dict(passed=error is None,config=c,checks=checks,records=records,error=error,training=False,
   tolerances=dict(reset=2e-5,commands_rad=1e-12,clock_s=1e-8,cable_rate_rad_s=.5),
   limitations=['signed sail intent becomes unsigned cable limit','native numerical bitwise repeatability not established','point-vessel scoring retained; native hull contacts logged separately']))
  for n in ['bridge.log','gazebo.log','xvfb.log']:
   if (R/'logs'/n).exists():shutil.copy2(R/'logs'/n,out/n)
 print('NATIVE_CHECK_PASS',checks,flush=True)

def plots(out,gate):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Circle
 data=json.loads(gate.read_text())['records']['response']
 t=[x['time'] for x in data];raw=np.array([x['raw'] for x in data]);ref=np.array([x['original_raw'] for x in data])
 target=np.array([x['target_angles'] for x in data]);d=[x['diagnostics'] for x in data]
 fig,axs=plt.subplots(2,2,figsize=(11,7))
 for a,idx,title in [(axs[0,0],3,'Yaw (rad)'),(axs[0,1],4,'Surge speed (m/s)')]:
  a.plot(t,ref[:,idx],label='Original 4DOF');a.plot(t,raw[:,idx],label='Yara native');a.set_title(title)
 axs[1,0].plot(t,np.abs(target[:,0]),label='Cable target')
 axs[1,0].plot(t,[x['cable_actual'] for x in d],label='Cable limit')
 axs[1,0].plot(t,[x['raw'][8] for x in d],label='Actual boom joint')
 axs[1,0].set_title('Native sail: limit is not boom angle (rad)')
 axs[1,1].plot(t,-target[:,1],label='Rudder target joint')
 axs[1,1].plot(t,[x['raw'][9] for x in d],label='Actual rudder joint')
 axs[1,1].set_title('Native rudder (rad)')
 for a in axs.flat:a.legend(fontsize=8);a.grid(alpha=.25);a.set_xlabel('Simulation time (s)')
 fig.tight_layout();fig.savefig(out/'native_response.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(1,3,figsize=(15,5))
 for a,name in zip(axs,['clear','single','switch']):
  p=json.loads((out/('policy_'+name+'.json')).read_text());scene=p['scene']
  xy=np.array([x['raw'][:2] for x in p['rows']]);a.plot(*xy.T,label='Yara native / frozen actor')
  ref=json.loads((R/'legacy4dof_20261108'/('policy_original_'+name+'.json')).read_text())
  a.plot(*np.array([x['raw'][:2] for x in ref['rows']]).T,'--',label='Original 4DOF / same actor')
  for o in scene['obstacles']:
   a.add_patch(Circle(o['center_xy'],o['entity_radius'],color='red',alpha=.3))
   a.add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],fill=False,color='orange'))
  a.scatter(*np.array(scene['goals']).T,marker='*',s=70,c='green');a.set_aspect('equal',adjustable='datalim')
  a.set_title(name+': '+p['summary']['reason']);a.set_xlabel('x (m)');a.set_ylabel('y (m)');a.grid(alpha=.25);a.legend(fontsize=7)
 fig.tight_layout();fig.savefig(out/'native_trajectories.png',dpi=150);plt.close(fig)

def capture(out):
 from native6dof_policy import capture_scene
 out=out.resolve();out.mkdir(parents=True,exist_ok=False)
 c=json.loads((R/'config_yara_transfer.json').read_text());scene=c['scenes'][1]
 tr=Transport(gazebo_args='--seed 61106');e=MigrationEnv('yara',tr,c);p=ObstacleController(mode='eval');rows=[]
 try:
  obs,_=e.reset(options=scene);p.reset(obs);rows.append(dict(raw=e.raw.copy(),time=0))
  for k in range(60):
   obs,reward,_,_,info=e.step(p.act(obs).action);native_state(info['diagnostics'])
   rows.append(dict(reward=reward,observation=obs,**info))
  receipts=capture_scene(tr,out,'single_demo',scene,rows)
  write(out,'capture.json',dict(scored=False,description='60-step actual frozen-policy demonstration; separate from the three scored tasks; camera advancement excluded',rows=rows,receipts=receipts))
 finally:
  p.close();e.close();tr.close()
  for n in ['bridge.log','gazebo.log','xvfb.log']:
   if (R/'logs'/n).exists():shutil.copy2(R/'logs'/n,out/n)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['check','plots','capture']);p.add_argument('--output',required=True,type=Path);p.add_argument('--gate',type=Path);a=p.parse_args()
 if not a.output.resolve().is_relative_to(R/'work'):raise ValueError('output must be in work')
 if a.stage=='check':check(a.output)
 elif a.stage=='capture':capture(a.output)
 else:plots(a.output,a.gate)
