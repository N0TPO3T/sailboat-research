from environment import *
from validate import save
import hashlib
receipts=[]
for scene in CONFIG['scenes']:
 for backend in ['original','yara']:
  path=R/'output'/('policy_'+scene['name']+'_'+backend+'.json');data=json.loads(path.read_text())
  e=MigrationEnv('original');e.reset(options=scene);g=e.modules.globals
  min_safe=math.inf;corrections=[];obs_error=0.;progress_error=0.;reward_error=0.;switched=False
  for previous,row in zip(data['rows'],data['rows'][1:]):
   before=np.asarray(previous['raw'],np.float32);raw=np.asarray(row['raw'],np.float32);old=raw.copy()
   if scene.get('switch_at')==previous['time'] and not switched:
    e.frame=ObstacleFrameFactory(e.obstacles,'boundary40').for_leg(before[:2],scene['goals'][1]);switched=True
   e.env.state=raw.copy();g.state=raw.copy();g.current_state=e.env.state[:12];g.current_action=np.array(row['physical_action'])
   e._progress(before);raw=e.env.state.copy()
   reward=float(e.env.calculate_reward(before,bool(row.get('integration_failed',False))))
   expected=e.frame.encode(raw,before);saved=np.asarray(row['observation'],np.float32)
   np.testing.assert_array_equal(expected,saved) # reward correction cannot change policy input
   obs_error=max(obs_error,float(np.max(np.abs(expected-saved))))
   progress_error=max(progress_error,float(np.max(np.abs(old[10:12]-raw[10:12]))))
   reward_error=max(reward_error,abs(reward-row['reward']))
   clearance=segment_circle_clearance(before[:2],raw[:2],e.obstacles);min_safe=min(min_safe,clearance['safety_m'])
   for k in ['entity_m','safety_m']:
    logged=row['clearance'][k]
    if logged is None:assert math.isinf(clearance[k])
    else:assert abs(logged-clearance[k])<1e-9
   assert row['time']==previous['time']+1
   if backend=='yara':
    assert abs(row['diagnostics']['dt']-1)<1e-8
    assert row['diagnostics']['motor_command']==row['diagnostics']['motor_applied_thrust']==0
   corrections.append(dict(time=row['time'],reward=reward,recorded_reward=row['reward'],corrected_progress=raw[10:12].tolist()))
  reached=np.linalg.norm(raw[:2]-scene['goals'][-1])<=CONFIG['goal_radius_m']
  assert data['success']==bool(reached and min_safe>0)
  assert len(data['rows'])-1<=CONFIG['limit_s']
  if backend=='original':assert reward_error==progress_error==0
  save('reward_recomputed_'+scene['name']+'_'+backend+'.json',dict(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),scope='exact inherited progress/reward on immutable actual trajectory; not new navigation',rows=corrections))
  receipts.append(dict(scene=scene['name'],backend=backend,steps=len(corrections),observations_exact=True,source_progress_max_error=progress_error,source_reward_max_error=reward_error,safety_recomputed=True,outcome_recomputed=True))
  e.close()
save('audit.json',dict(passed=True,rows=receipts,all_policy_inputs_exact=True,warning='Original Yara run rewards used float32 norm before source-exact progress extraction was fixed. Raw logs preserved; exact corrected rewards are separate. Policies and safety do not consume rewards, and every actual policy observation is bitwise unchanged.'))
print(json.dumps(receipts,indent=2))
