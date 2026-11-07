import json,time,traceback,math,os,subprocess
from pathlib import Path
import rospy
from std_srvs.srv import Trigger
from gazebo_msgs.srv import SpawnModel,DeleteModel,SetModelState
from gazebo_msgs.msg import ModelState
from geometry_msgs.msg import Pose
from tf.transformations import quaternion_from_euler
r=Path('/work/migration18'); ipc=r/'ipc'
rospy.init_node('migration18_bridge',anonymous=True)
rospy.wait_for_service('/gazebo/spawn_urdf_model',timeout=90)
rospy.wait_for_service('/migration/step',timeout=90)
spawn=rospy.ServiceProxy('/gazebo/spawn_urdf_model',SpawnModel)
sdfspawn=rospy.ServiceProxy('/gazebo/spawn_sdf_model',SpawnModel)
delete=rospy.ServiceProxy('/gazebo/delete_model',DeleteModel)
setstate=rospy.ServiceProxy('/gazebo/set_model_state',SetModelState)
step=rospy.ServiceProxy('/migration/step',Trigger)
models=[]
boat_name=None
def mark(name,xy,radius,color,collision=False,z=0.2):
 pose=Pose();pose.position.x=xy[0];pose.position.y=xy[1];pose.position.z=z;pose.orientation.w=1
 geom='<geometry><cylinder><radius>%s</radius><length>0.4</length></cylinder></geometry>'%radius
 xml='<sdf version="1.6"><model name="%s"><static>true</static><link name="link"><visual name="visual">%s<material><ambient>%s</ambient><diffuse>%s</diffuse></material></visual>%s</link></model></sdf>'%(name,geom,color,color,('<collision name="collision">'+geom+'</collision>') if collision else '')
 ans=sdfspawn(name,xml,'',pose,'world');assert ans.success,ans.status_message
 models.append(name)
def save_image(q):
 from sensor_msgs.msg import Image
 import numpy as np
 from PIL import Image as PIL
 if q.get('hide_water'):
  for visual in ['ocean_waves_visual','ocean_waves_below_visual']:
   message='name: "ocean_waves::ocean_waves_link::%s" parent_name: "ocean_waves::ocean_waves_link" visible: false'%visual
   result=subprocess.run(['gz','topic','-p','/gazebo/ocean/visual','-m',message],capture_output=True,text=True,timeout=10)
   assert result.returncode==0,result.stderr
 name='capture_'+str(q['id']); before=call(0);follow='_scene' not in q['filename'];bx,by=before['raw'][:2] if follow else q['xy'];dx,dy,z=q.get('offset',[-7,-8,5])
 yaw=math.atan2(-dy,-dx);pitch=math.atan2(z-q.get('look_z',1),math.hypot(dx,dy))
 xml='''<sdf version="1.6"><model name="%s"><static>true</static><link name="link"><sensor name="camera" type="camera"><pose>%s %s %s 0 %s %s</pose><always_on>true</always_on><update_rate>20</update_rate><camera><horizontal_fov>1.05</horizontal_fov><image><width>1600</width><height>900</height><format>R8G8B8</format></image><clip><near>0.1</near><far>2000</far></clip></camera><plugin name="camera" filename="libgazebo_ros_camera.so"><robotNamespace>/%s</robotNamespace><cameraName>%s</cameraName><imageTopicName>image_raw</imageTopicName><frameName>world</frameName></plugin></sensor></link></model></sdf>'''%(name,dx,dy,z,pitch,yaw,name,name)
 p=Pose();p.orientation.w=1;p.position.x=bx;p.position.y=by
 ans=sdfspawn(name,xml,'',p,'world');assert ans.success
 received=[];sub=rospy.Subscriber('/%s/%s/image_raw'%(name,name),Image,lambda m:received.append(m),queue_size=1)
 for i in range(300):
  if received:break
  state=call(10)
  if follow:
   camera=ModelState();camera.model_name=name;camera.reference_frame='world';camera.pose.orientation.w=1
   camera.pose.position.x=state['raw'][0];camera.pose.position.y=state['raw'][1]
   result=setstate(camera);assert result.success
  time.sleep(.05)
 assert received,('camera did not publish',rospy.get_published_topics())
 m=received[-1];a=np.frombuffer(m.data,dtype=np.uint8).reshape(m.height,m.step)[:,:m.width*3].reshape(m.height,m.width,3)
 if m.encoding=='bgr8':a=a[:,:,::-1]
 PIL.fromarray(a).save(r/'output'/q['filename']);sub.unregister();delete(name)
 return dict(camera_time=m.header.stamp.to_sec(),before=before,after=call(0),filename=q['filename'],extra_steps_excluded_from_results=True,terminal_boat_frozen_for_render=False,camera_follows_boat=follow,water_visual_hidden=bool(q.get("hide_water")))
def call(count,reset=False):
 rospy.set_param('/migration/count',count);rospy.set_param('/migration/reset',reset)
 ans=step();assert ans.success,ans.message
 return json.loads(ans.message)
(ipc/'ready').write_text('ready')
last=-1
while not rospy.is_shutdown():
 path=ipc/'request.json'
 if not path.exists():time.sleep(.005);continue
 try:q=json.loads(path.read_text())
 except Exception:time.sleep(.005);continue
 if q['id']==last:time.sleep(.005);continue
 last=q['id']
 try:
  op=q['op']
  if op=='close':break
  if op=='reset':
   for name in models:
    delete(name)
   models.clear()
   if boat_name:delete(boat_name)
   boat_name='migration_boat_'+str(last)
   rospy.set_param('/migration/model',boat_name)
   raw=q['raw'];p=Pose();p.position.x=raw[0];p.position.y=raw[1];p.position.z=0.
   quat=quaternion_from_euler(raw[2],0,raw[3]);p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w=quat
   ans=spawn(boat_name,(r/'boat.urdf').read_text(),'',p,'world');assert ans.success,ans.status_message
   s=ModelState();s.model_name=boat_name;s.pose=p;s.reference_frame='world'
   s.twist.linear.x=math.cos(raw[3])*raw[4]-math.sin(raw[3])*raw[5]
   s.twist.linear.y=math.sin(raw[3])*raw[4]+math.cos(raw[3])*raw[5]
   s.twist.angular.x=raw[6];s.twist.angular.z=raw[7]
   ans=setstate(s);assert ans.success
   for i,o in enumerate(q['obstacles']):mark('obstacle_%d'%i,o['center_xy'],o['entity_radius'],'0.8 0.2 0.1 1',True)
   for i,goal in enumerate(q['goals']):mark('goal_%d'%i,goal,3,'0.1 0.9 0.2 1')
   rospy.set_param('/migration/freeze',False)
   rospy.set_param('/migration/cable',0.);rospy.set_param('/migration/rudder',0.)
   rospy.set_param('/migration/wx',float(q['wind'][0]));rospy.set_param('/migration/wy',float(q['wind'][1]))
   result=call(0,True)
  elif op=='step':
   rospy.set_param('/migration/cable',float(q['cable']));rospy.set_param('/migration/rudder',float(q['rudder']))
   result=call(100)
  elif op=='capture':
   for i,xy in enumerate(q['trace'][::max(1,len(q['trace'])//60)]):mark('track_%s_%d'%(last,i),xy,.7,'0.95 0.8 0.1 1',False,.4)
   result=save_image(q)
  else:raise ValueError(op)
  result=dict(id=last,result=result)
 except Exception:result=dict(id=last,error=traceback.format_exc())
 tmp=ipc/'response.tmp';tmp.write_text(json.dumps(result));tmp.replace(ipc/'response.json')
