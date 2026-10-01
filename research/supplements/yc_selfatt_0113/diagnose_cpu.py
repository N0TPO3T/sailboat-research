from pathlib import Path
import os,sys,json,random,time,hashlib,importlib.util
import numpy as np,torch
torch.set_num_threads(1)
root=Path('/home/ot/Students/hs/sailboat-research')
dst=root/'research/supplements/yc_selfatt_0113'
sys.path.insert(0,str(dst));import utils_lstm_selfatt as net,globals
envpath=root/'sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_V2.py'
sp=importlib.util.spec_from_file_location('hs_diag_v2',envpath);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
results={'scope':'2 paired seeds; GitHub obst-v2 proxy, historical environment unverified; no extra sensor/actuator wrapper','environment_sha256':hashlib.sha256(envpath.read_bytes()).hexdigest(),'cases':[],'compatibility':[]}
for step in [9000,14400]:
 def load(role):
  return torch.load(dst/'model'/f'saclstm_s14obst-selfatt_0113_{role}{step}.pth',map_location='cpu',weights_only=True)
 actor=net.Actor(18,2,(256,256)).eval()
 critic=net.Double_Q_Critic(18,2,(256,256),(256,128)).eval()
 actor.load_state_dict(load('actor'),strict=True);critic.load_state_dict(load('q_critic'),strict=True)
 for model in [actor,critic]:
  assert all(torch.isfinite(p).all() for p in model.parameters())
 norm=net.ZScoreNormalizer(18,torch.device('cpu'));ns=load('normalizer');assert torch.isfinite(ns['mean']).all() and torch.isfinite(ns['var']).all() and (ns['var']>=0).all();norm.load_state_dict(ns)
 results['compatibility'].append({'checkpoint':step,'actor_critic_strict_load':True,'finite':True,'normalizer_dim':18})
 for seed in [0,1]:
  random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
  env=m.Sailboat_obst_v2(render_mode=None);obs,_=env.reset(seed=seed)
  setup={'wind':list(globals.w0),'obstacles':[list(x) for x in globals.obstacles],'heading':float(obs[3])}
  prev=obs.copy();pa=np.zeros(2,dtype=np.float32);actor.reset_hidden_state()
  min_dist=float('inf');total=0.;beg=time.monotonic();term=trunc=False
  with torch.no_grad():
   for i in range(1000):
    kw={'current_state':norm.normalize(torch.tensor(obs).unsqueeze(0)),'prev_state':norm.normalize(torch.tensor(prev).unsqueeze(0)),'prev_action':torch.tensor(pa).unsqueeze(0),'single_step_mode':True,'env_ids':['diag'],'deterministic':True}
    a,_=actor(**kw);pa=a[0].numpy();prev=obs.copy()
    obs,reward,term,trunc,_=env.step(pa*env.action_space.high)
    assert np.isfinite(obs).all() and np.isfinite(reward) and np.isfinite(pa).all()
    if globals.obstacles:min_dist=min(min_dist,min(float(np.linalg.norm(obs[:2]-np.array(x))) for x in globals.obstacles))
    total+=float(reward)
    if term or trunc:break
    if time.monotonic()-beg>90:break
  distance=float(np.linalg.norm(obs[:2]-obs[12:14]))
  row={'checkpoint':step,'seed':seed,'steps':i+1,'terminated':bool(term),'truncated':bool(trunc),'reached_goal':distance<=10,'collision_observed_at_step_boundary':min_dist<40,'min_obstacle_distance':min_dist if np.isfinite(min_dist) else None,'reward':total,'final_distance':distance,'wall_seconds':time.monotonic()-beg,'initial_scenario':setup,'budget_stop':not(term or trunc)}
  results['cases'].append(row);print(json.dumps(row),flush=True);env.close()
out=root/'research/outputs/yc_selfatt_diagnostic.json';out.write_text(json.dumps(results,indent=2));print('SAVED',out,flush=True)
