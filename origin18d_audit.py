"""Source-defined origin18D acceptance; no 6DOF or real hull reconstruction claim."""
from environment import *
from validate import clean
from sailboat_routing.obstacle_candidate import loading_paths
import argparse,re,runpy,traceback
D=R/os.environ['MIGRATION18_RUN']
if D.parent!=R or not D.name.startswith('legacy4dof_'):raise ValueError('run path')
def save(name,value):
 with (D/name).open('x') as f:json.dump(clean(value),f,indent=2)
def preflight():
 D.mkdir(exist_ok=True)
 if (D/'acceptance_manifest.json').exists():raise FileExistsError('previous run preserved')
 c=json.loads((R/'config_legacy4dof.json').read_text())
 assert c['physics_mode']=='legacy4dof' and c['actuator_mode']=='signed'
 assert c.get('action_mode','legacy_delta')=='legacy_delta'
 assert c['policy_dt']==1 and c['physics_dt']==.01
 assert c['scenes']==CONFIG['scenes']
 e=MigrationEnv('original',config=c);policy=ObstacleController(mode='eval')
 try:
  root=Path('/home/ot/Students/hs/sailboat-routing-v0');paths=loading_paths()
  selected=[Path(v) for v in e.modules.paths.values()]+[Path(v) for v in policy.modules.paths.values()]+[Path(paths[k]) for k in ['actor','normalizer']]
  selected += [R/'frozen/src/sailboat_routing'/n for n in ['runtime.py','continuous.py','r6_controller.py','obstacle_candidate.py','metrics.py','planner.py','frames.py','r7_dynamic.py']]
  identity=[]
  for p in selected:
   relative=p.relative_to(R/'frozen');source=root/relative
   assert p.read_bytes()==source.read_bytes(),str(relative)
   identity.append(dict(path=str(p),original=str(source),byte_equal=True))
  header=(R/'legacy_parameters.hh').read_text()
  parameters={k:float(v) for k,v in re.findall(r'constexpr double P_(\w+) = ([^;]+);',header)}
  assert parameters==e.env.par
  old=json.loads((R/'legacy4dof_20261108/parameters.json').read_text())
  assert old['parameters']==e.env.par
  np.testing.assert_array_equal(old['mass_inverse'],e.env.M_inv)
  assert not policy.actor.training and all(not x.requires_grad for x in policy.actor.parameters())
  assert policy.normalizer.state_dict()['mean'].shape==(18,)
  save('acceptance_manifest.json',dict(config=c,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),actual_loading=paths,identity=identity,parameters=e.env.par,mass_inverse=e.env.M_inv,existing_asset_index='ASSET_HASHES.json',scope='all source-defined 4DOF/18D behavior; original hull CAD and 6DOF/contact physics not defined',geometry_source='frozen/third_party/senior/sailboat_s14.py render: pygame.draw.circle, radius 5 screen pixels; not physical hull radius',training=False,actor_mode='eval',seed=c['seed'],max_scored_episodes=6,max_steps_per_episode=900,tolerances=dict(raw=[.001,.001,1e-4,1e-4,1e-4,1e-4,1e-4,1e-4,1e-6,1e-6,1e-3,1e-3,0,0],observation=[.001,.001,1e-4,1e-4,1e-4,1e-4,1e-4,1e-4,1e-6,1e-6,1e-3,1e-3,0,0,.001,1e-4,.001,1e-4],action=1e-4,reward=1e-3,clock=1e-8,derivative=1e-9,discrete='exact')))
 finally:policy.close();e.close()
 import validate
 validate.save=save
 validate.semantic()
 runpy.run_path(str(R/'edge_checks.py'),run_name='__main__')
 print('PREFLIGHT_PASS',len(parameters),len(identity),flush=True)
def wind_kernel():
 import legacy_reference
 m=SeniorModules();e=m.environment.Sailboat_nowind_last();legacy_reference.globals=m.globals
 cases=[];expected=[]
 try:
  for speed in [0.,3.,8.,12.]:
   for angle in np.linspace(-np.pi,np.pi,8,endpoint=False):
    state=np.array([0.,0.,.2,angle/2,1.2,-.1,.04,-.03]);sail=.4;rudder=-.2
    m.globals.w_change_v=speed;m.globals.w_change_d=angle
    cases.append([*state,sail,rudder,speed*np.cos(angle),speed*np.sin(angle)])
    expected.append(legacy_reference.state_derivatives(e,state,np.zeros(2),0.,sail,rudder,0.,0.))
  result=subprocess.run([str(R/'build/legacy_probe')],input='\n'.join(' '.join(map(str,v)) for v in cases)+'\n',text=True,capture_output=True,check=True)
  actual=np.array([[float(v) for v in line.split()] for line in result.stdout.splitlines()])
  maximum=np.max(np.abs(actual-expected),axis=0);passed=bool(max(maximum)<=1e-9)
  save('wind_kernel_gate.json',dict(passed=passed,tolerance=1e-9,cases=cases,expected=expected,actual=actual,max_error=maximum))
  assert passed,maximum
  print('WIND_KERNEL_PASS',max(maximum),flush=True)
 finally:e.close()
def postflight():
 m=json.loads((D/'acceptance_manifest.json').read_text());tol=m['tolerances'];checks=[]
 for file in ['semantic.json','edge_checks.json','kernel_gate.json','response_gate.json','reset_gate.json','dryden_gate.json','wind_kernel_gate.json']:
  assert json.loads((D/file).read_text())['passed'],file
 try:
  for scene in m['config']['scenes']:
   name=scene['name'];a=json.loads((D/('policy_original_'+name+'.json')).read_text());b=json.loads((D/('policy_yara_'+name+'.json')).read_text())
   assert a['scene']==b['scene']==scene and a['reason']==b['reason'] and a['success']==b['success']
   assert len(a['rows'])==len(b['rows'])
   raw_a=np.array([x['raw'] for x in a['rows']]);raw_b=np.array([x['raw'] for x in b['rows']]);raw_error=np.max(np.abs(raw_a-raw_b),axis=0)
   assert np.all(raw_error<=np.array(tol['raw'])),(name,'raw',raw_error)
   obs_error=np.max(np.abs(np.array([x['observation'] for x in a['rows'][1:]])-np.array([x['observation'] for x in b['rows'][1:]])),axis=0)
   assert np.all(obs_error<=np.array(tol['observation'])),(name,'observation',obs_error)
   action_error=max(float(np.max(np.abs(np.array(x['action'])-y['action']))) for x,y in zip(a['rows'][1:],b['rows'][1:]))
   reward_error=max(abs(x['reward']-y['reward']) for x,y in zip(a['rows'][1:],b['rows'][1:]))
   assert action_error<=tol['action'] and reward_error<=tol['reward'],(name,action_error,reward_error)
   assert a['switches']==b['switches']
   for x,y in zip(a['rows'][1:],b['rows'][1:]):
    assert x['collision']==y['collision'] and x['goal_reached']==y['goal_reached'] and x['time']==y['time']
    np.testing.assert_array_equal(x['wind_next'],y['wind_next'])
    d=y['diagnostics'];assert d['physics_mode']=='legacy4dof' and d['body_kinematic']
    assert abs(d['dt']-1)<tol['clock'] and d['motor_command']==d['motor_applied_thrust']==0
   obstacles=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],o['safety_buffer']) for o in scene['obstacles'])
   clearance=min((segment_circle_clearance(x['raw'][:2],y['raw'][:2],obstacles)['safety_m'] for x,y in zip(b['rows'],b['rows'][1:])),default=math.inf)
   assert b['success']==bool(b['reason']=='arrived' and clearance>0)
   checks.append(dict(scene=name,steps=len(b['rows'])-1,reason=b['reason'],success=b['success'],min_safety_m=clearance,raw_max_error=raw_error,observation_max_error=obs_error,action_max_error=action_error,reward_max_error=reward_error,max_position_error=float(np.max(np.linalg.norm(raw_a[:,:2]-raw_b[:,:2],axis=1))),discrete_rules_equal=True))
  save('acceptance.json',dict(passed=True,source_defined_migration_passed=True,original_3d_hull_reconstruction=False,training=False,paired=checks,manifest='acceptance_manifest.json'))
 except Exception:
  save('acceptance.json',dict(passed=False,paired=checks,error=traceback.format_exc()));raise
 print('ACCEPTANCE_PASS',json.dumps(clean(checks)),flush=True)
def plots():
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Circle
 manifest=json.loads((D/'acceptance_manifest.json').read_text())
 assert json.loads((D/'acceptance.json').read_text())['passed']
 fig,axes=plt.subplots(1,3,figsize=(15,5));bounds=[]
 for ax,scene in zip(axes,manifest['config']['scenes']):
  name=scene['name']
  for backend,label,style in [('original','Original 18D / 4DOF','-'),('yara','Gazebo migrated 4DOF','--')]:
   data=json.loads((D/('policy_'+backend+'_'+name+'.json')).read_text());xy=np.array([x['raw'][:2] for x in data['rows']])
   ax.plot(*xy.T,style,label=label);ax.plot(*xy[-1],'x');bounds.extend(xy.tolist())
  for o in scene['obstacles']:
   ax.add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],color='orange',alpha=.15))
   ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='red',alpha=.4))
   cx,cy=o['center_xy'];radius=o['entity_radius']+o['safety_buffer'];bounds.extend([[cx-radius,cy-radius],[cx+radius,cy+radius]])
  goals=np.array(scene['goals']);bounds.extend(goals.tolist());ax.scatter(*goals.T,c='green',marker='*',s=60)
  ax.set_title(name+' | '+data['reason']);ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.grid(alpha=.25);ax.legend(fontsize=8)
 bounds=np.array(bounds);lo=bounds.min(0)-20;hi=bounds.max(0)+20
 for ax in axes:ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1])
 fig.tight_layout();fig.savefig(D/'origin18d_paired.png',dpi=160);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(11,7))
 for backend,label,style in [('original','Original 18D / 4DOF','-'),('yara','Gazebo migrated 4DOF','--')]:
  rows=json.loads((D/('response_'+backend+'.json')).read_text())['rows'];t=[x['time'] for x in rows];raw=np.array([x['raw'] for x in rows])
  for ax,value in zip(axes.flat,[raw[:,:2],np.unwrap(raw[:,3])*180/np.pi,raw[:,4],raw[:,8]*180/np.pi]):
   if value.ndim==2:ax.plot(*value.T,style,label=label)
   else:ax.plot(t,value,style,label=label)
 for ax,title in zip(axes.flat,['Trajectory (m)','Heading (deg)','Surge (m/s)','Actual sail angle (deg)']):
  ax.set_title(title);ax.grid(alpha=.25);ax.legend(fontsize=8)
 fig.tight_layout();fig.savefig(D/'origin18d_response.png',dpi=160);plt.close(fig)
 print('PLOTS_PASS',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['preflight','wind_kernel','postflight','plots']);args=p.parse_args();globals()[args.stage]()
