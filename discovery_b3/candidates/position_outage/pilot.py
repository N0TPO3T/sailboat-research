import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']: os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
import pathlib,io,csv,json,time,datetime,hashlib
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=pathlib.Path(__file__).resolve().parent
O=P/'results'; O.mkdir(exist_ok=True)
started=datetime.datetime.now(datetime.timezone.utc).isoformat(); clock=time.perf_counter()
def load(name):
 b=(P/name).read_bytes(); s=b.decode().splitlines(); s=s if b.endswith(b'\n') else s[:-1]
 return np.genfromtxt(io.StringIO('\n'.join(s)),delimiter=',',names=True)
a=load('imu_prefix_8MiB.csv'); b=load('lidar_poses_prefix_3MiB.csv')
tbase=float(a['time'][0]); ta=(a['time']-tbase)*1e-6; tb=(b['utc_micro']-tbase)*1e-6
w=np.column_stack([a[k] for k in ['wx','wy','wz']]); acc=np.column_stack([a[k] for k in ['ax','ay','az']])
pos=np.column_stack([b[k] for k in ['x','y','z']]); vel=np.column_stack([b[k] for k in ['vel_x_enuref','vel_y_enuref','vel_z_enuref']]); vb=np.column_stack([b[k] for k in ['vel_x_body','vel_y_body','vel_z_body']]); wb=np.column_stack([b[k] for k in ['angvel_x','angvel_y','angvel_z']]); ang=np.column_stack([b[k] for k in ['ang_x','ang_y','ang_z']])
# Author C1(x) C2(y) C3(z): transpose of active Rz(z) Ry(y) Rx(x).
R=Rotation.from_euler('xyz',ang).as_matrix().transpose(0,2,1)
rot_error=np.linalg.norm(np.einsum('nij,nj->ni',R,vb)-vel,axis=1)
T=np.loadtxt(P/'T_lidar_imu.txt'); lever=T[:3,3]
assert np.allclose(T[:3,:3],np.eye(3))
pos=pos+np.einsum('nij,j->ni',R,lever)
vel=vel+np.einsum('nij,nj->ni',R,np.cross(wb,lever))
assert np.max(rot_error)<1e-6,rot_error.max()
def interp(t,x): return np.column_stack([np.interp(np.atleast_1d(t),tb,x[:,j]) for j in range(x.shape[1])])
def rawmean(lo,hi): return w[(ta>=lo)&(ta<hi)].mean(axis=0)
# Contract check only: same-clock gyro/sign/units vs independent reference. No parameter fitting from future.
wc=interp(ta,wb); delta=w-wc
contract={'reference_velocity_transform_max_error_mps':float(rot_error.max()),'raw_gyro_reference_axis_correlation':[float(np.corrcoef(w[:,i],wc[:,i])[0,1]) for i in range(3)],'raw_gyro_minus_reference_median_radps':np.median(delta,axis=0).tolist(),'imu_span_s':float(ta[-1]),'reference_span_s':float(tb[-1]),'mean_accel_norm_mps2':float(np.mean(np.linalg.norm(acc,axis=1))),'lever_arm_m':lever.tolist(),'time_max_gap_s':float(np.max(np.diff(ta)))}
(O/'contract.json').write_text(json.dumps(contract,indent=2))
assert min(contract['raw_gyro_reference_axis_correlation'])>.2,'Gyro unit/frame contract uncertain: stop before pilot'
metrics=[]; traces={}; win=[]
for start in range(40,521,60):
 if start+60>min(ta[-1],tb[-1]): continue
 j=np.searchsorted(tb,start,side='right')-1
 p0=interp(start,pos)[0]; v0=interp(start,vel)[0]; R0=R[j] # latest reference sample, no future pose interpolation
 hist=(tb>=start-20)&(tb<start)
 course=np.unwrap(np.arctan2(vel[hist,1],vel[hist,0])); rate=float(np.polyfit(tb[hist]-start,course,1)[0]); speed=np.linalg.norm(vel[hist,:2],axis=1)
 kind='low_speed' if np.median(speed)<.5 else ('turning' if abs(rate)>np.pi/180 else 'ordinary')
 bias=rawmean(start-20,start)-np.mean(interp(ta[(ta>=start-20)&(ta<start)],wb),axis=0)
 ids=np.where((ta>start)&(ta<=start+60))[0]; times=np.r_[start,ta[ids],start+60]; times=np.unique(times); dt=np.diff(times); rel=times-start
 truth=interp(times,pos); vv=interp(times,vel)
 # Scorer truth is kept outside each model's state update.
 cv=p0[None,:2]+rel[:,None]*v0[None,:2]
 if abs(rate)<1e-9: ctr=cv.copy()
 else:
  si=np.sin(rate*rel); co=np.cos(rate*rel)
  ctr=p0[None,:2]+np.column_stack([(si*v0[0]-(1-co)*v0[1])/rate,((1-co)*v0[0]+si*v0[1])/rate])
 methods={'CV':cv,'CTR':ctr}
 h0=np.arctan2(R0[1,0],R0[0,0]); vnorm=np.linalg.norm(v0[:2]); c0=np.arctan2(v0[1],v0[0])
 for label,offset in [('gyro_raw',np.zeros(3)),('gyro_bias',bias)]:
  rr=R0.copy(); xy=p0[:2].copy(); path=[xy.copy()]
  for k,d in enumerate(dt):
   # Forward sample-and-hold: only last raw measurement at or before interval start.
   idx=np.searchsorted(ta,times[k],side='right')-1
   omega=w[max(idx,0)]-offset
   mid=rr@Rotation.from_rotvec(omega*d*.5).as_matrix()
   heading=np.arctan2(mid[1,0],mid[0,0]); c=c0+heading-h0
   xy=xy+vnorm*np.array([np.cos(c),np.sin(c)])*d
   rr=rr@Rotation.from_rotvec(omega*d).as_matrix(); path.append(xy.copy())
  methods[label]=np.array(path)
 normal=np.column_stack([-vv[:,1],vv[:,0]]); norms=np.linalg.norm(normal,axis=1); normal[norms<.1]=np.array([-v0[1],v0[0]]); normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-10)
 # Reference heading and side slip diagnostic used ONLY after predictions complete.
 hs=np.unwrap(np.arctan2(R[:,1,0],R[:,0,0])); href=np.interp(times,tb,hs); cr=np.unwrap(np.arctan2(vv[:,1],vv[:,0])); slip=np.unwrap(cr-href)
 meta={'start_s':start,'kind':kind,'past_COG_rate_degps':rate*180/np.pi,'past_speed_mps':float(np.median(speed)),'gyro_bias_radps':bias.tolist(),'speed_change_max_mps':float(np.max(np.abs(np.linalg.norm(vv[:,:2],axis=1)-vnorm))),'course_heading_offset_change_max_deg':float(np.max(np.abs(slip-slip[0]))*180/np.pi)}; win.append(meta)
 traces[str(start)]={'t':rel,'truth':truth[:,:2],**methods}
 for name,path in methods.items():
  err=path-truth[:,:2]; lateral=np.abs(np.sum(err*normal,axis=1)); dist=np.linalg.norm(err,axis=1)
  row={'start_s':start,'kind':kind,'method':name}
  for h in [10,30,60]: row[f'error_{h}_m']=float(np.interp(h,rel,dist)); row[f'lateral_{h}_m']=float(np.interp(h,rel,lateral))
  row['max_lateral_m']=float(lateral.max())
  for budget in [2,5,10]:
   hit=np.flatnonzero(lateral>budget); row[f'first_{budget}m_s']=float(rel[hit[0]]) if len(hit) else 60.; row[f'crossed_{budget}m']=bool(len(hit))
  metrics.append(row)
with (O/'scores.csv').open('w',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=list(metrics[0]));wr.writeheader();wr.writerows(metrics)
(O/'windows.json').write_text(json.dumps(win,indent=2)); np.savez_compressed(O/'traces.npz',**{s+'_'+k:v for s,d in traces.items() for k,v in d.items()})
summary={}
for method in methods:
 rows=[x for x in metrics if x['method']==method]
 summary[method]={k:float(np.mean([x[k] for x in rows])) for k in ['error_10_m','error_30_m','error_60_m','lateral_60_m','max_lateral_m','first_2m_s','first_5m_s','first_10m_s']}
 summary[method]['count_crossed_5m']=sum(x['crossed_5m'] for x in rows)
(O/'summary.json').write_text(json.dumps(summary,indent=2))
fig,axs=plt.subplots(1,2,figsize=(11,4.2),constrained_layout=True)
for name in methods:
 rows=[x for x in metrics if x['method']==name]; axs[0].plot([x['start_s'] for x in rows],[x['error_60_m'] for x in rows],'-o',label=name);axs[1].plot([10,30,60],[summary[name][f'error_{h}_m'] for h in [10,30,60]],'-o',label=name)
axs[0].set(xlabel='Window start in recording (s)',ylabel='Horizontal error at 60 s (m)',title='All fixed windows; one real recording')
axs[1].set(xlabel='Propagation horizon (s)',ylabel='Mean horizontal error (m)',title='Oracle initialization; no future pose updates')
for ax in axs: ax.grid(alpha=.3);ax.legend()
fig.savefig(O/'propagation_errors.png',dpi=180);plt.close(fig)
# Fixed examples: first window + strongest gyro-bias degradation relative to CV. Selection is explicit visualization only.
starts=[40,max(range(40,521,60),key=lambda s:next(x['error_60_m'] for x in metrics if x['start_s']==s and x['method']=='gyro_bias')-next(x['error_60_m'] for x in metrics if x['start_s']==s and x['method']=='CV'))]
fig,axs=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
for ax,s in zip(axs,starts):
 d=traces[str(s)];p=d['truth'][0]
 ax.plot(*(d['truth']-p).T,'k',lw=2.5,label='Reference (score only)')
 for name in methods: ax.plot(*(d[name]-p).T,label=name)
 ax.set(xlabel='East offset (m)',ylabel='North offset (m)',title=f'Window {s}s: '+('preselected first' if ax is axs[0] else 'largest gyro-vs-CV degradation'));ax.axis('equal');ax.grid(alpha=.3);ax.legend(fontsize=8)
fig.savefig(O/'propagation_examples.png',dpi=180);plt.close(fig)
receipt={'start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.perf_counter()-clock,'pid':os.getpid(),'worker':1,'threads':1,'gpu':0,'python':os.sys.executable,'windows':len(win),'method_window_rows':len(metrics),'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'input_sha256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['imu_prefix_8MiB.csv','lidar_poses_prefix_3MiB.csv','T_lidar_imu.txt','PROTOCOL.md']},'exit_status':'completed'}
(O/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({'contract':contract,'summary':summary,'receipt':receipt},indent=2))
