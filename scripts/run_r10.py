"""R10 finite discriminative controls; legacy implementations remain untouched."""
import os,sys,json,time,copy,math,hashlib,subprocess,concurrent.futures,multiprocessing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import run_r6,run_r8
from sailboat_routing.r6_controller import ObstacleFrame,ObstacleFrameFactory
from sailboat_routing.r8_planner import SampledSupervisor
from sailboat_routing.navigation import _write_json

class MatchedFrame(ObstacleFrame):
    def encode(self,raw,previous=None):
        if self.distance_mode not in ('matched_center','matched_clipped'):
            return super().encode(raw,previous)
        near=[]
        for i,o in enumerate(self.obstacles):
            delta=np.asarray(o.center_xy)-np.asarray(raw[:2]);d=float(np.linalg.norm(delta))
            effective=max(0.,d-o.exclusion_radius+40.)
            if effective<=150:
                a=math.atan2(delta[1],delta[0])-float(raw[3]);a=math.atan2(math.sin(a),math.cos(a))
                near.append((effective,a,i,d))
        # Exactly boundary40's (distance, bearing) selection/order; only numerical distance differs.
        near.sort(key=lambda x:(x[0],x[1]))
        extra=[]
        for eff,a,i,d in near[:2]:extra.extend([min(d,150.) if self.distance_mode=='matched_clipped' else d,a])
        extra.extend([0.]*(4-len(extra)))
        return np.concatenate((self.base.encode(raw,previous),np.asarray(extra,dtype=np.float32)))

class MatchedFactory(ObstacleFrameFactory):
    def for_leg(self,start,goal):
        return MatchedFrame(self.base_type.for_leg(start,goal),self.obstacles,self.distance_mode)
from sailboat_routing.frames import LocalFrame
MatchedFactory.base_type=LocalFrame

class NominalTriggeredHold(SampledSupervisor):
    """Predict nominal only. On same causal nominal-risk test hold incumbent, never rank alternatives."""
    def plan(self,p,heading,velocity,current,goal,t,obs,history,commands,oh,frame,old_action,pending=()):
        if t<self.until:return tuple(self.held)
        incumbent=None if self.held is not None else current
        nominal=self.base.plan(p,heading,velocity,incumbent,goal,t,obs)
        nearby=any(o['valid'] and np.linalg.norm(np.asarray(o['position'])-p)<600 for o in obs)
        if t<self.next_plan or not nearby:
            if self.held is not None:
                self.events.append(dict(time=t,event='release',selected='nominal',target=list(nominal),reason='outside_prediction_range'));self.held=None
            return nominal
        begin=time.perf_counter();hold=self.cfg.get('period',15);self.next_plan=t+hold;self.model.estimate(history)
        pred=self.model.rollout(history,commands,oh,frame,np.asarray(nominal),old_action,self.cfg.get('horizon',60),self.chart.obstacles,np.asarray(goal),copy.deepcopy(self.base),0,pending,self.cfg.get('goal_delay',0))
        feasible=pred['valid'] and pred['min_margin']>=self.cfg.get('guard',30) and not pred['integration_failed']
        name='nominal' if feasible or current is None else 'continue';q=nominal if name=='nominal' else current
        previous=self.held;self.held=None if name=='nominal' else list(q);self.until=t+hold if self.held is not None else 0
        event='ordinary' if self.held is None and previous is None else 'release' if self.held is None else 'enter' if previous is None else 'reevaluate'
        self.events.append(dict(time=t,event=event,selected=name,target=list(q),nominal_predicted_feasible=feasible,alternative_safety_evaluated=False))
        self.predictions.append(dict(time=t,position=list(map(float,p)),wind_estimate=self.model.wind.tolist(),selected=name,candidates=[dict(name='nominal',target=list(nominal),hold=0,prediction=pred,feasible=feasible,cost=pred['terminal_distance'])],wall_seconds=time.perf_counter()-begin))
        return tuple(q)

def worker(job):
    if job.get('domain','static')=='static':
        old=run_r6.ObstacleFrameFactory;run_r6.ObstacleFrameFactory=MatchedFactory
        try:return run_r6.worker(job)
        finally:run_r6.ObstacleFrameFactory=old
    old=run_r8.SampledSupervisor
    if job['config'].get('r10_nominal_hold'):run_r8.SampledSupervisor=NominalTriggeredHold
    try:return run_r8.worker(job)
    finally:run_r8.SampledSupervisor=old

def main():
    manifest=Path(sys.argv[1]).resolve();batch=json.loads(manifest.read_text());run=Path(batch['run']).resolve()
    assert run.is_relative_to((ROOT/'runs').resolve())
    plan=json.loads((run/'plan.json').read_text());assert time.time()<plan['deadline_epoch']
    folder=manifest.with_suffix('');folder.mkdir(exist_ok=False);src=folder/'source';src.mkdir()
    files=[Path(__file__),ROOT/'scripts/run_r6.py',ROOT/'scripts/run_r8.py',ROOT/'scripts/run_r1.py']+list((ROOT/'src/sailboat_routing').glob('*.py'))
    for f in files:(src/f.name).write_bytes(f.read_bytes())
    _write_json(folder/'provenance.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sources={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},workers=4,threads=1,gpu_hours=0,parent_pid=os.getpid(),started=time.time(),command=sys.argv))
    jobs=[]
    for j in batch['jobs']:
        j=copy.deepcopy(j);j.update(out=str(folder/(j['scene']['id']+'__'+j['variant'])),deadline=plan['deadline_epoch'],round=1);jobs.append(j)
    rows=[];start=time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        for f in concurrent.futures.as_completed([pool.submit(worker,j) for j in jobs]):
            row=f.result();rows.append(row);_write_json(folder/'rows.json',rows);print('R10',len(rows),'/',len(jobs),row['scene_id'],row['variant'],row['success'],row['time_s'],flush=True)
    _write_json(folder/'completion.json',dict(complete=True,episodes=len(rows),wall_seconds=time.time()-start,cpu_seconds=sum(x['cpu_seconds'] for x in rows)))
if __name__=='__main__':main()