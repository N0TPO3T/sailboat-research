import os,sys,json,time,math,concurrent.futures,multiprocessing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import SeniorModules
from sailboat_routing.continuous import ContinuousPhysics
from sailboat_routing.navigation import bind_time_indexed_wind
from sailboat_routing.wind_fields import SyntheticWindField
import numpy as np
wrap=lambda x:math.atan2(math.sin(x),math.cos(x))
def worker(j):
 out_path=ROOT/'runs'/j['batch']/(j['id']+'__'+j['method']+'.json')
 if out_path.exists():raise FileExistsError(out_path)
 start=time.time();cpu=time.process_time();m=SeniorModules();p=ContinuousPhysics(m,total_time_limit=j.get('horizon',1200),world_radius_limit=10000)
 raw=p.reset(j['seed'],j.get('wind',90));raw[:2]=j.get('start',[0,0]);raw[3]=math.radians(j.get('heading',0));raw[4]=j.get('speed',2.)
 p.env.state[:]=raw;m.globals.state=raw.copy();p.raw=raw.copy()
 field=SyntheticWindField(j['seed']+100000,math.radians(j.get('wind',90)),j.get('profile','stable'),horizon=j.get('horizon',1200)+1,base_speed=j.get('wind_speed',8.))
 bind_time_indexed_wind(p,field);center=np.array(j.get('center',[0,0.]));R=j.get('radius',100.);q=1;leg=1;trace=[];mode='start';integration_failed=False;last_u=raw[4];sailmag=0.2
 for t in range(j.get('horizon',1200)):
  if time.time()>1791472420:raise TimeoutError('shared deadline')
  raw=p.raw.copy();pos=raw[:2];psi=raw[3];u,v=raw[4:6];wind=m.globals.w_change_d;ws=m.globals.w_change_v
  d=float(np.linalg.norm(pos-center));bearing=math.atan2(center[1]-pos[1],center[0]-pos[0]);a=math.atan2(pos[1]-center[1],pos[0]-center[0]);method=j['method'];heading=bearing;mode='approach'
  if method=='heading':heading=math.radians(j.get('desired',0))
  elif method in ['phase','phase_adaptive']:
   if R*j.get('inner',.45)<d<R*j.get('outer',1.) and math.cos(bearing-wind)>0:
    heading=bearing+(math.pi/2 if math.cos(a-(wind+math.pi/2))>math.cos(a-(wind-math.pi/2)) else -math.pi/2);mode='round'
   if d<R*j.get('inner',.45):
    heading=wind+math.pi if u>j.get('surge_floor',0) else wind+math.pi-math.radians(50)*(np.sign(v) if abs(v)>1e-8 else q);mode='hold'
  elif method=='orbit':
   heading=a+math.pi/2+math.atan2(d-R*j.get('orbit_radius',.55),R*.3);mode='orbit'
  elif method in ['shuttle','shuttle_no_tack']:
   beam=np.array([math.cos(wind+math.pi/2),math.sin(wind+math.pi/2)]);target=center+leg*R*j.get('span',.5)*beam
   if np.linalg.norm(pos-target)<R*.2:leg=-leg;target=center+leg*R*j.get('span',.5)*beam
   heading=math.atan2(target[1]-pos[1],target[0]-pos[0]);mode='shuttle'
  if mode!='hold' and method not in ['heading','center_no_tack','shuttle_no_tack']:
   if math.cos(wind-heading)+math.cos(math.radians(j.get('closehaul',50)))<0:heading=wind+math.pi+q*math.radians(j.get('closehaul',50))
   else:q=1 if math.sin(wind-heading)>0 else -1
  error=wrap(psi-heading);rudder=np.clip(-j.get('kp',0.7)*error-j.get('kd',1.5)*raw[7],-math.pi/6,math.pi/6)
  if u<0 and j.get('reverse_steering',True):rudder=-rudder
  awx=ws*math.cos(wind-psi)-u;awy=ws*math.sin(wind-psi)-v;alpha=math.atan2(awy,-awx)
  sail=np.clip(alpha*.5,-math.pi/2,math.pi/2)
  if method=='phase_adaptive':
   desired_accel=-.05*u+.001*d;measured_accel=u-last_u;sailmag=np.clip(sailmag-.2*(desired_accel-measured_accel),abs(alpha*.5),min(abs(alpha),math.pi/2))
   sail=math.copysign(sailmag,alpha)
  if mode=='hold' and u>j.get('surge_floor',0):sail=np.clip(alpha,-math.pi/2,math.pi/2)
  desired=np.array([sail,rudder]);targets=np.array([p.env.target_sail_angle,p.env.target_rudder_angle]);deg=np.clip(np.rint(np.degrees(desired-targets)),-10,10)
  command=np.clip((np.radians(deg)+1e-8)/(math.pi/18),-1,1);last_u=u
  trace.append(dict(t=t,raw=raw.tolist(),d=d,desired_heading=wrap(heading),mode=mode,wind=wind,wind_speed=ws,command=command.tolist()))
  _,_,_,done,info=p.step(command)
  if info['integration_failed']:
   integration_failed=True;break
 trace.append(dict(t=len(trace),raw=p.raw.tolist(),d=float(np.linalg.norm(p.raw[:2]-center)),desired_heading=None,mode='terminal',wind=m.globals.w_change_d,wind_speed=m.globals.w_change_v,command=None))
 x=np.array([z['d'] for z in trace[:-1]]);outs=x>R;best=cur=0
 for b in outs:cur=cur+1 if b else 0;best=max(best,cur)
 result=dict(id=j['id'],method=method,inside_fraction=float(np.sum(~outs)/j.get('horizon',1200)),observed_fraction=float(np.mean(~outs)),max_outside_s=best,max_radius=float(max(z['d'] for z in trace)),rms_radius=float(np.sqrt(np.mean(x*x))),completed=(len(trace)-1==j.get('horizon',1200) and not integration_failed),integration_failed=integration_failed,duration_s=len(trace)-1,actuator_variation_rad=float(np.abs(np.diff(np.array([z['raw'][8:10] for z in trace]),axis=0)).sum()),max_heel_deg=float(max(abs(math.degrees(z['raw'][2])) for z in trace)),cpu_s=time.process_time()-cpu,wall_s=time.time()-start,source_paths=m.paths,job=j)
 out=ROOT/'runs'/j['batch'];out.mkdir(exist_ok=True,parents=True);(out/(j['id']+'__'+method+'.json')).write_text(json.dumps(dict(result=result,trace=trace)))
 p.close();return result
if __name__=='__main__':
 jobs=json.loads(Path(sys.argv[1]).read_text());print('ROOT',ROOT,flush=True)
 out=ROOT/'runs'/jobs[0]['batch'];out.mkdir(parents=True,exist_ok=True);(out/'runner_source.py').write_bytes(Path(__file__).read_bytes())
 with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
  for r in pool.map(worker,jobs):print(json.dumps(r),flush=True)




