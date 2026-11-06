import json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
R=Path(__file__).resolve().parent;O=R/'output';cfg=json.loads((R/'config.json').read_text())
plt.rcParams.update({'font.size':10,'figure.dpi':140})
colors={'original':'#1765a0','yara':'#db5b27'}
def load(name):return json.loads((O/name).read_text())
def sceneplot(ax,scene):
 for o in scene['obstacles']:
  ax.add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],fill=False,edgecolor='#aa3333',linestyle='--'))
  ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='#aa3333',alpha=.4))
 g=np.array(scene['goals']);ax.scatter(g[:,0],g[:,1],marker='*',s=90,c='green',label='Targets')
 ax.scatter([0],[0],c='black',s=20,label='Start');ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.grid(alpha=.2)
fig,axs=plt.subplots(2,3,figsize=(14,8))
for j,scene in enumerate(cfg['scenes']):
 for i,b in enumerate(colors):
  ax=axs[i,j];sceneplot(ax,scene)
  p=O/('policy_'+scene['name']+'_'+b+'.json')
  if p.exists():
   d=json.loads(p.read_text());s=np.array([r['raw'] for r in d['rows']]);ax.plot(s[:,0],s[:,1],color=colors[b],label=b)
   ax.scatter(s[-1,0],s[-1,1],marker='x',color=colors[b])
   ax.set_title(scene['name']+' / '+b+'\n'+d['reason']+'; '+str(len(s)-1)+' s')
  ax.legend(fontsize=7)
# Share world-coordinate limits within each task column; circles keep the same visual size.
for j,scene in enumerate(cfg['scenes']):
 points=[np.array(scene['goals']),np.array([[0,0]])]
 for b in colors:
  p=O/('policy_'+scene['name']+'_'+b+'.json')
  if p.exists():points.append(np.array([x['raw'][:2] for x in json.loads(p.read_text())['rows']]))
 for obstacle in scene['obstacles']:
  c=np.array(obstacle['center_xy']);radius=obstacle['entity_radius']+obstacle['safety_buffer'];points.append(np.array([c-radius,c+radius]))
 points=np.concatenate(points);lo=points.min(axis=0)-30;hi=points.max(axis=0)+30
 for i in range(2):
  axs[i,j].set_xlim(lo[0],hi[0]);axs[i,j].set_ylim(lo[1],hi[1]);axs[i,j].set_aspect('equal',adjustable='box')
fig.suptitle('Actual paired trajectories | same coordinate limits within each column');fig.tight_layout();fig.savefig(O/'paired_trajectories.png');plt.close(fig)
fig,axs=plt.subplots(2,3,figsize=(14,8))
for name,style in [('hold','-'),('rudder_pos','--'),('rudder_neg',':'),('sail','-.')]:
 for b,c in colors.items():
  d=load('response_'+name+'_'+b+'.json');s=np.array([r['raw'] for r in d['rows']]);t=np.array([r['time'] for r in d['rows']]);target=np.array([r['target_angles'] for r in d['rows']])
  label=b+'/'+name
  axs[0,0].plot(s[:,0],s[:,1],style,c=c,label=label)
  for ax,y in [(axs[0,1],np.unwrap(s[:,3])*180/np.pi),(axs[0,2],s[:,4]),(axs[1,0],s[:,8]*180/np.pi),(axs[1,1],s[:,9]*180/np.pi),(axs[1,2],target[:,0]*180/np.pi)]:
   ax.plot(t,y,style,c=c,label=label)
for ax,title in zip(axs.flat,['Position x/y (m)','Heading (deg)','Body u (m/s)','Actual sail (deg)','Actual rudder (deg)','Accumulated sail target (deg)']):
 ax.set_title(title);ax.grid(alpha=.2);ax.set_xlabel('s' if ax is not axs[0,0] else 'x (m)')
axs[0,0].legend(fontsize=7);fig.suptitle('Fixed actions: native physical differences remain after sign correction')
fig.tight_layout();fig.savefig(O/'fixed_response.png');plt.close(fig)
summary=[]
for scene in cfg['scenes']:
 for b in colors:
  p=O/('policy_'+scene['name']+'_'+b+'.json')
  if not p.exists():continue
  d=json.loads(p.read_text());s=np.array([r['raw'] for r in d['rows']]);row=dict(scene=scene['name'],backend=b,success=d['success'],reason=d['reason'],steps=len(s)-1,final_distance_m=float(np.linalg.norm(s[-1,:2]-scene['goals'][-1])),path_length_m=float(np.linalg.norm(np.diff(s[:,:2],axis=0),axis=1).sum()),switches=len(d['switches']),wall_s=d['wall_s'],min_safety=d['rows'][-1].get('min_safety'))
  if b=='yara':
   dt=[r['diagnostics']['dt'] for r in d['rows'][1:]];row['max_clock_error']=max(abs(x-1) for x in dt)
   row['motor_zero']=all(r['diagnostics']['motor_command']==r['diagnostics']['motor_applied_thrust']==0 for r in d['rows'][1:])
  summary.append(row)
(O/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))

fig,axs=plt.subplots(1,2,figsize=(14,5))
scene=cfg['scenes'][1];sceneplot(axs[0],scene)
d=load('policy_single_original.json');x=np.array([v['raw'] for v in d['rows']]);axs[0].plot(x[:,0],x[:,1],color=colors['original']);axs[0].set_title('Original: actual logged scene and trajectory')
axs[1].imshow(plt.imread(O/'actual_single_scene.png'));axs[1].axis('off');axs[1].set_title('Yara: actual Gazebo camera (post-episode)')
fig.suptitle('Same static obstacle: entity radius 30 m, safety buffer 60 m')
fig.tight_layout();fig.savefig(O/'scene_comparison.png');plt.close(fig)
