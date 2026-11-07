import os,json,time,math,hashlib,zipfile
from pathlib import Path
import numpy as np
import rospy,torch,gymnasium as gym,esailor_gym
from stable_baselines3 import SAC,PPO
from gazebo_msgs.srv import SpawnModel,GetModelState
from geometry_msgs.msg import Pose
from sensor_msgs.msg import Image
from PIL import Image as PIL
from rosgraph_msgs.msg import Clock
from tf.transformations import quaternion_from_euler

out=Path('/work/transfer_audit');out.mkdir(exist_ok=True)
torch.set_num_threads(1);np.random.seed(7)
rospy.init_node('yara_report_capture',anonymous=True)
rospy.wait_for_service('/gazebo/spawn_urdf_model',timeout=60)
clock=[0.];rospy.Subscriber('/clock',Clock,lambda m:clock.__setitem__(0,m.clock.to_sec()))
env=gym.make('Eboat53-v0');base=env.unwrapped
base.wind_directions=np.array([90]);base.wind_speedVec=np.array([5.0])
obs,_=env.reset(seed=7)
policyroot=Path('/work/workspace/src/Yara_OVE/esailor/policy')
receipts=[];models={}
for kind,cls in [('PPO',PPO),('SAC',SAC)]:
 p=policyroot/f'esailor_{kind}_53_A3232_C3232.zip'
 m=cls.load(str(p),device='cpu');models[kind]=m
 with zipfile.ZipFile(p) as z:
  version=z.read('_stable_baselines3_version').decode();d=json.loads(z.read('data'))
 receipts.append({'model':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'saved_sb3':version,'observation_shape':list(m.observation_space.shape),'action_shape':list(m.action_space.shape),'num_timesteps':m.num_timesteps,'policy_kwargs':str(m.policy_kwargs),'gamma':m.gamma,'batch_size':m.batch_size,'learning_rate':str(m.learning_rate),'ent_coef':str(m.ent_coef),'seed':m.seed,'saved_fields':{k:d.get(k) for k in ['n_steps','n_epochs','buffer_size','learning_starts','train_freq','gradient_steps','tau']}})
(out/'checkpoint_audit.json').write_text(json.dumps(receipts,indent=2))
get=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)
rows=[]
for i in range(24):
 a,_=models['PPO'].predict(obs,deterministic=True)
 obs,r,term,trunc,_=env.step(a)
 st=get('eboat_1','world')
 rows.append({'step':i,'sim_time':clock[0],'action':a.tolist(),'obs':obs.tolist(),'reward':float(r),'position':[st.pose.position.x,st.pose.position.y,st.pose.position.z],'terminated':bool(term),'truncated':bool(trunc)})
 if term or trunc:break
(out/'demo_trajectory.json').write_text(json.dumps({'scope':'visualization only; original PPO checkpoint; fixed wind parameter 90 degrees and 5 m/s; not performance evaluation','rows':rows},indent=2))
spawn=rospy.ServiceProxy('/gazebo/spawn_sdf_model',SpawnModel)
st=get('eboat_1','world');bx,by=st.pose.position.x,st.pose.position.y
views=[('boat_close',(-7,-8,5),1.4),('boat_side',(0,-10,2.8),1.2),('ocean_overview',(-20,-25,23),0)]
received={};subs=[]
for name,offset,tz in views:
 dx,dy,z=offset;x,y=bx+dx,by+dy
 yaw=math.atan2(-dy,-dx);pitch=math.atan2(z-tz,math.hypot(dx,dy))
 sdf=f'''<sdf version="1.6"><model name="{name}"><static>true</static><link name="link"><sensor name="camera" type="camera"><pose>{x} {y} {z} 0 {pitch} {yaw}</pose><always_on>true</always_on><update_rate>2</update_rate><camera><horizontal_fov>1.05</horizontal_fov><image><width>1600</width><height>900</height><format>R8G8B8</format></image><clip><near>0.1</near><far>1500</far></clip></camera><plugin name="ros_camera" filename="libgazebo_ros_camera.so"><robotNamespace>/{name}</robotNamespace><cameraName>{name}</cameraName><imageTopicName>image_raw</imageTopicName><cameraInfoTopicName>camera_info</cameraInfoTopicName><frameName>world</frameName></plugin></sensor></link></model></sdf>'''
 pose=Pose();pose.orientation.w=1.0
 # Camera pose is relative to the identity model.

 result=spawn(name,sdf,name,pose,'world');assert result.success,result.status_message

 subs.append(rospy.Subscriber(f'/{name}/{name}/image_raw',Image,lambda m,n=name:received.__setitem__(n,m),queue_size=1))
base.unpause();deadline=time.monotonic()+45
while len(received)<len(views) and time.monotonic()<deadline:time.sleep(.2)
base.pause()
assert len(received)==len(views), (list(received),rospy.get_published_topics())
for name,m in received.items():
 a=np.frombuffer(m.data,dtype=np.uint8).reshape(m.height,m.step)[:,:m.width*3].reshape(m.height,m.width,3)
 if m.encoding=='bgr8':a=a[:,:,::-1]
 assert m.encoding in ('rgb8','bgr8'),m.encoding
 PIL.fromarray(a).save(out/(name+'.png'))
(out/'capture_receipt.json').write_text(json.dumps({'source':'Gazebo ROS camera sensor, actual Yara world; not generated illustration','checkpoint':'PPO_53','camera_time':{n:m.header.stamp.to_sec() for n,m in received.items()},'views':views,'boat_position_before_capture':[bx,by],'gpu':False},indent=2))
print('CAPTURE_PASS',list(received),flush=True)
env.close()
