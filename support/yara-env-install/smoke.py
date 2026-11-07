import json,time,random
from pathlib import Path
import numpy as np
import rospy
import gymnasium as gym
import esailor_gym
from gazebo_msgs.srv import GetModelState
from rosgraph_msgs.msg import Clock
from stable_baselines3 import SAC
import torch

random.seed(7);np.random.seed(7);torch.manual_seed(7);torch.set_num_threads(1)
rospy.init_node('yara_install_smoke',anonymous=True)
rospy.wait_for_service('/gazebo/spawn_urdf_model',timeout=50)
clock=[None]
sub=rospy.Subscriber('/clock',Clock,lambda m:clock.__setitem__(0,m.clock.to_sec()))
env=gym.make('Eboat53-v0')
obs,info=env.reset(seed=7)
assert np.asarray(obs).shape==(5,) and np.isfinite(obs).all()
get=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)
start=get('eboat_1','world');assert start.success
policy=SAC('MlpPolicy',env,device='cpu',buffer_size=16,learning_starts=100,seed=7,policy_kwargs={'net_arch':[16,16]})
rows=[]
for i in range(8):
 action,_=policy.predict(obs,deterministic=True)
 action[2]=0.0 # No engine for this smoke test; no training or saved-policy evaluation.
 obs,reward,terminated,truncated,info=env.step(action)
 assert np.asarray(obs).shape==(5,) and np.isfinite(obs).all() and np.isfinite(reward)
 assert env.action_space.contains(action)
 state=get('eboat_1','world');assert state.success
 rows.append({'step':i,'clock':clock[0],'action':action.tolist(),'obs':np.asarray(obs).tolist(),'reward':float(reward),'position':[state.pose.position.x,state.pose.position.y,state.pose.position.z],'terminated':bool(terminated),'truncated':bool(truncated)})
 if terminated or truncated:break
assert len(rows)>=2 and rows[-1]['clock']>rows[0]['clock']
assert np.isfinite(np.array([r['position'] for r in rows])).all()
report={'status':'PASS','scope':'installation smoke only; untrained SAC inference, no learning','gym_env':'Eboat53-v0','python_obs_dtype':str(np.asarray(obs).dtype),'declared_obs_dtype':str(env.observation_space.dtype),'torch':torch.__version__,'gpu_used':False,'rows':rows,'clock_advanced':True}
Path('/work/logs/SMOKE_RESULT.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
env.close()
