"""Small R9 saved-state timing probe; never advances an actual task."""
import sys,os,time,json,cProfile,pstats,copy,concurrent.futures,multiprocessing,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import numpy as np
from sailboat_routing.r8_model import CausalModel
from sailboat_routing.r8_planner import AvailabilityRelay
from sailboat_routing.planner import StaticMap,CircleObstacle
from sailboat_routing.frames import LocalFrame
from sailboat_routing.obstacle_candidate import ObstacleController
from sailboat_routing.r7_dynamic import replay

def inputs(file,t):
 d=json.loads(Path(file).read_text());tr=d['trajectory'];p=next(x for x in d['predictions'] if x['time']==t);h=[np.array(x['raw'],dtype=np.float32) for x in tr[:t+1]];cmd=[np.array(x['command'],dtype=np.float32) for x in tr[1:t+1]];oh=[x['observations'] for x in tr[:t+1]]
 frame=LocalFrame.for_leg(h[0][:2],tr[0]['target'])
 for c in d['changes']:
  if c['applied_at']<=t:frame=LocalFrame.for_leg(tr[c['applied_at']]['raw'][:2],c['target'])
 static=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],60.) for o in d['scene'].get('static',[]));chart=StaticMap((-2500,d['scene']['distance_m']+2500,-3000,3000),static,grid_resolution=25.)
 policy=ObstacleController(mode='eval');obs,_=replay(policy,frame,static,oh,h,cmd);act=policy.act(obs).action;policy.close();assert np.array_equal(act,np.array(tr[t+1]['command'],dtype=np.float32))
 previous=[x for x in d['predictions'] if x['time']<t];return d,p,h,cmd,oh,frame,static,chart,act,previous

def work(job):
 file,t=job;d,p,h,cmd,oh,frame,static,chart,act,previous=inputs(file,t);measure=[]
 for optimized in [False,True]:
  instrument=False
  from sailboat_routing.r9_model import CausalModel as FastModel
  cold=time.perf_counter();m=(FastModel if optimized else CausalModel)();cold=time.perf_counter()-cold
  if previous:m.wind=np.array(previous[-1]['wind_estimate']);m.fitted=True
  profiler=cProfile.Profile();start=time.perf_counter();cpu=time.process_time()
  if instrument:profiler.enable()
  a=time.perf_counter();m.estimate(h);fit=time.perf_counter()-a;preds=[]
  for c in p['candidates']:
   preds.append(m.rollout(h,cmd,oh,frame,c['target'],act,60,static,np.array(d['scene']['goal']),AvailabilityRelay(chart,d['config']),c['hold']))
  if instrument:profiler.disable()
  elapsed=time.perf_counter()-start;cpu=time.process_time()-cpu;stats=[]
  if instrument:
   st=pstats.Stats(profiler)
   for (filename,line,func),(cc,nc,tt,ct,callers) in st.stats.items():stats.append(dict(file=filename,line=line,function=func,calls=nc,self_seconds=tt,cumulative_seconds=ct))
  measure.append(dict(optimized=optimized,instrumented=instrument,wall_seconds=elapsed,cpu_seconds=cpu,cold_model_seconds=cold,wind_fit_seconds=fit,rollout_steps=sum(len(x['path'])-1 for x in preds),max_path_difference=max(float(np.max(np.abs(np.array(x['path'])-np.array(c['prediction']['path'])))) if len(x['path'])==len(c['prediction']['path']) else 1e9 for x,c in zip(preds,p['candidates'])),profile=sorted(stats,key=lambda x:x['cumulative_seconds'],reverse=True)[:60]));m.close()
 return dict(source=file,time=t,history_length=len(h),candidates=len(p['candidates']),selected=p['selected'],measurements=measure)

def main():
 run=Path(sys.argv[1]).resolve();old=ROOT/'runs/r8_closedloop_20261005T062543Z';spec=[('development2/confirm_mixed_3__sampled/trace.json',10),('development2/confirm_mixed_3__sampled/trace.json',115),('development2/confirm_mixed_3__sampled/trace.json',130),('confirmation/r8new_endpoint_5__sampled/trace.json',267)]
 for name in ['long/r8long_3000_crossing__sampled/trace.json','long/r8long_5000_crossing__sampled/trace.json']:
  d=json.loads((old/name).read_text());p=max(d['predictions'],key=lambda x:x['wall_seconds']);spec.append((name,p['time']))
 result=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
  for f in concurrent.futures.as_completed([pool.submit(work,(str(old/name),t)) for name,t in spec]):
   x=f.result();result.append(x);(run/'replay_equivalence.json').write_text(json.dumps(result,indent=2));print(x['time'],x['history_length'],x['candidates'],[(m['wall_seconds'],m['max_path_difference']) for m in x['measurements']],flush=True)
 (run/'replay_hardware.txt').write_text(subprocess.check_output(['lscpu'],text=True)+'\nload:'+str(os.getloadavg())+'\nworkers=4, numerical_threads=1, no GPU; warm wall and profiler passes separate\n')
if __name__=='__main__':main()
