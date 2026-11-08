"""Isolated migration. Shared frozen semantics; two physics backends."""
import os,sys,json,time,subprocess,math,ast,inspect,textwrap,copy
import gymnasium as gym
from pathlib import Path
R=Path(__file__).resolve().parent
os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(R/'.tmp'))
sys.path.insert(0,str(R/'frozen/src'))
import numpy as np
from sailboat_routing.runtime import SeniorModules
from sailboat_routing.continuous import ContinuousPhysics
from sailboat_routing.r6_controller import ObstacleFrameFactory,change_reference
from sailboat_routing.obstacle_candidate import ObstacleController
from sailboat_routing.metrics import segment_circle_clearance
from sailboat_routing.planner import CircleObstacle
CONFIG=json.loads((R/'config.json').read_text())
class Transport:
 def __init__(self,world=None,gazebo_args=None):
  self.ipc=R/'ipc';self.i=0
  for n in ['ready','request.json','response.json']:
   (self.ipc/n).unlink(missing_ok=True)
  self.log=(R/'logs/bridge.log').open('w')
  self.proc=subprocess.Popen([str(R.parent/'run-yara-visual.sh'),'bash','/work/migration18/container.sh',world or '/work/migration18/ocean.world',gazebo_args or ''],stdout=self.log,stderr=subprocess.STDOUT)
  deadline=time.monotonic()+100
  while not (self.ipc/'ready').exists():
   if self.proc.poll() is not None:raise RuntimeError('container exited; logs/bridge.log')
   if time.monotonic()>deadline:raise TimeoutError('ROS startup')
   time.sleep(.1)
 def request(self,op,**kw):
  self.i+=1;q=dict(id=self.i,op=op,**kw)
  tmp=self.ipc/'request.tmp';tmp.write_text(json.dumps(q));tmp.replace(self.ipc/'request.json')
  deadline=time.monotonic()+90
  while time.monotonic()<deadline:
   p=self.ipc/'response.json'
   if p.exists():
    response=json.loads(p.read_text())
    if response['id']==self.i:
     if 'error' in response:raise RuntimeError(response['error'])
     return response['result']
   if self.proc.poll() is not None:raise RuntimeError('bridge stopped')
   time.sleep(.002)
  raise TimeoutError(op)
 def close(self):
  self.i+=1
  p=self.ipc/'request.tmp';p.write_text(json.dumps(dict(id=self.i,op='close')));p.replace(self.ipc/'request.json')
  try:self.proc.wait(timeout=30)
  except subprocess.TimeoutExpired:self.proc.terminate();self.proc.wait(timeout=15)
  self.log.close()
def accumulate(target,physical):
 degree=np.pi/180
 return np.clip(np.asarray(target)+np.asarray(physical)//degree*degree,[-np.pi/2,-np.pi/6],[np.pi/2,np.pi/6])
def from_gazebo(diag):
 raw=np.array(diag['raw'],dtype=np.float32)
 # Legacy force/kinematic conventions: roll sign and foil angular coordinate.
 raw[[2,6,8,9]]*=-1
 return raw
def shared_progress(environment):
 # Extract only the six audited progress assignments; never maintain another formula.
 original=environment.Sailboat_nowind_last.step
 tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
 body=tree.body[0].body
 start=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='pre_dis' and isinstance(n.value,ast.Call))
 selected=copy.deepcopy(body[start:start+6])
 expected=['pre_dis','cur_dis','globals.current_state[10]','pre_x_dis','cur_x_dis','globals.current_state[11]']
 assert [ast.unparse(n.targets[0]) for n in selected]==expected
 fn=ast.parse('def progress(previous_state): pass').body[0];fn.body=selected
 unit=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(unit)
 ns=dict(original.__globals__);exec(compile(unit,'<audited-original-progress>','exec'),ns)
 return ns['progress']
class MigrationEnv(gym.Env):
 def __init__(self,backend,transport=None,config=None):
  assert backend in ['original','yara'];self.backend=backend;self.transport=transport;self.config=config or CONFIG
  self.modules=SeniorModules();self.physics=ContinuousPhysics(self.modules,total_time_limit=self.config['limit_s'],world_radius_limit=self.config['world_radius_m'])
  self.env=self.physics.env;self.high=self.env.action_space.high.astype(float)
  self.action_space=gym.spaces.Box(-1.,1.,shape=(2,),dtype=np.float32)
  self.observation_space=gym.spaces.Box(-np.inf,np.inf,shape=(18,),dtype=np.float32)
  self._progress=shared_progress(self.modules.environment)
  self.action_mode=self.config.get('action_mode','legacy_delta')
  if self.action_mode not in ['legacy_delta','native_absolute']:raise ValueError('action_mode')
  if self.action_mode=='native_absolute':
   assert backend=='yara' and self.config['physics_mode']=='native' and self.config['actuator_mode']=='native'
   assert self.config.get('sail_force_model','native')=='native'

 def reset(self,*,seed=None,options=None):
  scene=options or self.config['scenes'][0];self.scene=scene
  raw=self.physics.reset(self.config['seed'] if seed is None else seed)
  raw[:]=np.asarray(self.config['initial'],dtype=np.float32);raw[12:14]=scene['goals'][0]
  self.obstacles=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],o['safety_buffer']) for o in scene['obstacles'])
  g=self.modules.globals;wind=self.config['wind'];g.w_change_v=float(np.linalg.norm(wind[:2]));g.w_change_d=math.atan2(wind[1],wind[0])
  self.wind_mode=self.config.get('wind_mode','fixed')
  if self.wind_mode not in ['fixed','legacy_dryden']:raise ValueError('wind_mode')
  for prefix in ['w_ini','w_last']:
   setattr(g,prefix+'_v',g.w_change_v);setattr(g,prefix+'_d',g.w_change_d)
  self.env.dryden_state_u=0.;self.env.dryden_state_v=0.;self.env.dryden_params['V']=g.w_change_v
  self.env.update_wind=(self.modules.environment.Sailboat_nowind_last.update_wind.__get__(self.env) if self.wind_mode=='legacy_dryden' else lambda:None)
  self.target=np.zeros(2);self.t=0.;self.min_safety=math.inf;self.goal=np.array(scene['goals'][0],dtype=np.float32)
  if self.backend=='yara':
   reset_raw=raw.copy();reset_raw[[2,6,8,9]]*=-1
   self.diag=self.transport.request('reset',raw=reset_raw.tolist(),wind=wind,obstacles=scene['obstacles'],goals=scene['goals'],actuator_mode=self.config.get('actuator_mode','native'),physics_mode=self.config.get('physics_mode','native'),initial_6dof=self.config.get('initial_6dof',{}),fluid_density=self.config.get('fluid_density'),sail_force_model=self.config.get('sail_force_model','native'))
   measured=from_gazebo(self.diag);measured[12:14]=self.goal
   if not np.allclose(measured[:10],raw[:10],atol=2e-5,rtol=0):raise AssertionError(('reset mismatch',measured,raw))
   raw=measured;self.clock0=self.diag['clock']
  self.raw=raw.copy();self.env.state=raw.copy();self.physics.raw=raw.copy();g.state=raw.copy();g.current_state=self.env.state[:12];g.current_time=0.
  self.frame=ObstacleFrameFactory(self.obstacles,'boundary40').for_leg(raw[:2],self.goal)
  self.history=[raw.copy()];self.commands=[]
  return self.frame.encode(raw),dict(raw=raw.copy())
 def set_goal(self,goal,policy=None):
  self.goal=np.asarray(goal,dtype=np.float32)
  self.physics.set_goal(goal);self.raw[12:14]=self.goal
  self.frame=ObstacleFrameFactory(self.obstacles,'boundary40').for_leg(self.raw[:2],goal)
  if policy is not None:return change_reference(policy,self.frame,self.history,self.commands)[0]
  return self.frame.encode(self.raw,self.history[-2] if len(self.history)>1 else None)
 def step(self,action):
  action=np.asarray(action,dtype=float)
  if action.shape!=(2,) or not np.isfinite(action).all() or np.any(np.abs(action)>1):raise ValueError('normalized action')
  before=self.raw.copy()
  if self.action_mode=='legacy_delta':
   physical=self.modules.network.Action_adapter(action,self.high)
   reward_action=physical.copy()
   self.target=accumulate(self.target,physical)
  else:
   # Native joint coordinates: cable opening [0,90] deg and rudder [-60,60] deg.
   # Repeating an action holds its absolute target; [0,0] commands 45 deg / 0 deg.
   physical=np.array([(action[0]+1)*np.pi/4,action[1]*np.pi/3])
   reward_action=physical-self.target
   self.target=physical.copy()
  if self.backend=='original':
   raw,reward,reached,truncated,info=self.physics.step(action);self.t=info['time']
   np.testing.assert_allclose(self.target,[self.env.target_sail_angle,self.env.target_rudder_angle],rtol=0,atol=1e-12)
   self.diag=dict(clock=self.t,dt=1.,motor_command=0,motor_applied_thrust=0,cable_actual=None)
  else:
   g=self.modules.globals
   step_wind=(self.config['wind'] if self.wind_mode=='fixed' else [g.w_change_v*math.cos(g.w_change_d),g.w_change_v*math.sin(g.w_change_d),0.])
   command=(dict(cable=float(self.target[0]),rudder=float(self.target[1])) if self.action_mode=='native_absolute'
            else dict(cable=abs(float(self.target[0])),rudder=-float(self.target[1]),sail_target=-float(self.target[0])))
   self.diag=self.transport.request('step',wind=step_wind,**command)
   assert abs(self.diag['dt']-1)<1e-8,self.diag
   self.t+=1
   assert abs(self.diag['clock']-self.clock0-self.t)<1e-8
   raw=from_gazebo(self.diag);raw[12:14]=self.goal
   g=self.modules.globals;self.env.state=raw.copy();g.state=raw.copy();g.current_state=self.env.state[:12];g.current_action=reward_action;g.current_time=self.t
   self._progress(before);raw=self.env.state.copy()
   if self.wind_mode=='legacy_dryden':
    with self.physics._rng():self.env.update_wind()
   reward=self.env.calculate_reward(before,False);reached=self.env.check_done()
   self.physics.raw=raw.copy();truncated=self.t>=self.config['limit_s'] or np.linalg.norm(raw[:2])>=self.config['world_radius_m']
   info=dict(integration_failed=False)
  if not np.isfinite(raw).all():raise FloatingPointError('nonfinite state')
  clearance=segment_circle_clearance(before[:2],raw[:2],self.obstacles);self.min_safety=min(self.min_safety,clearance['safety_m'])
  collision=clearance['entity_m']<=0
  self.raw=raw.copy();self.history.append(raw.copy());self.commands.append(action.astype(np.float32))
  info.update(action_mode=self.action_mode,reward_action_delta=reward_action.tolist(),physical_contact=bool(self.diag.get('contact_points',0)),wind_next=[self.modules.globals.w_change_v,self.modules.globals.w_change_d],time=self.t,raw=raw.copy(),physical_action=physical.copy(),target_angles=self.target.tolist(),clearance=clearance,min_safety=self.min_safety,collision=collision,goal_reached=bool(reached),diagnostics=self.diag)
  return self.frame.encode(raw,before),float(reward),bool(collision or reached),bool(truncated),info
 def close(self):self.physics.close()
