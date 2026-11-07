"""Pinned-repository baseline entry, not a claim of paper-exact reproduction."""
import argparse,json,time,random,zipfile,io
from pathlib import Path
import numpy as np,torch,rospy,gymnasium as gym,esailor_gym
from stable_baselines3 import SAC,PPO

p=argparse.ArgumentParser()
p.add_argument('--mode',choices=['probe','train'],default='probe')
p.add_argument('--algo',choices=['SAC','PPO'],default='SAC')
p.add_argument('--seed',type=int,default=7)
p.add_argument('--steps',type=int,default=500000)
a=p.parse_args()
torch.set_num_threads(1);torch.manual_seed(a.seed);random.seed(a.seed);np.random.seed(a.seed)
rospy.init_node('yara_baseline',anonymous=True)
rospy.wait_for_service('/gazebo/spawn_urdf_model',timeout=60)
env=gym.make('Eboat53-v0');cls={'SAC':SAC,'PPO':PPO}[a.algo]
out=Path('/work/transfer_audit');out.mkdir(exist_ok=True)
if a.mode=='probe':
 path=Path('/work/workspace/src/Yara_OVE/esailor/policy')/f'esailor_{a.algo}_53_A3232_C3232.zip'
 model=cls.load(str(path),device='cpu')
 with zipfile.ZipFile(path) as z:state=torch.load(io.BytesIO(z.read('policy.pth')),map_location='cpu')
 actual=model.policy.state_dict()
 assert state.keys()==actual.keys() and all(torch.equal(v,actual[k]) for k,v in state.items())
 obs,_=env.reset(seed=a.seed);rows=[]
 for i in range(8):
  act,_=model.predict(obs,deterministic=True)
  obs,r,term,trunc,_=env.step(act)
  assert np.isfinite(obs).all() and np.isfinite(r)
  rows.append({'step':i,'obs':obs.tolist(),'action':act.tolist(),'reward':float(r),'terminated':bool(term),'truncated':bool(trunc)})
  if term or trunc:break
 (out/f'{a.algo}_probe.json').write_text(json.dumps({'status':'PASS','saved_policy_tensors_exact':True,'scope':'8-step interface check, not task evaluation','rows':rows},indent=2))
 print(a.algo,'PROBE_PASS',len(rows))
else:
 run=out/f'train_{a.algo}_seed{a.seed}_{int(time.time())}';run.mkdir()
 kw=dict(policy='MlpPolicy',env=env,device='cpu',seed=a.seed,learning_rate=3e-4,gamma=.99,batch_size=64,ent_coef=.001,verbose=1)
 if a.algo=='SAC':
  kw.update(policy_kwargs={'activation_fn':torch.nn.ReLU,'net_arch':{'pi':[32,32],'qf':[32,32]}},buffer_size=1000000,learning_starts=100,tau=.005,train_freq=1,gradient_steps=1)
 else:
  kw.update(policy_kwargs={'activation_fn':torch.nn.ReLU,'net_arch':{'pi':[32,32],'vf':[32,32]}},n_steps=2048,n_epochs=10,gae_lambda=.95,clip_range=.2,normalize_advantage=True,vf_coef=.5,max_grad_norm=.5)
 (run/'request.json').write_text(json.dumps(vars(a),indent=2))
 model=cls(**kw);model.learn(total_timesteps=a.steps);model.save(str(run/'model'))
 if a.algo=='SAC':model.save_replay_buffer(str(run/'replay.pkl'))
env.close()
