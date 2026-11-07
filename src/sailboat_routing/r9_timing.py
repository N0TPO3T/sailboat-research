"""One opaque pending result. Planning state cannot affect execution before ready.
Offline emulation of independent planning executor and a1Hz feedback executor.
Planning service uses measured wall time; fixed slots discard overruns.
"""
import math,time
import numpy as np
from .r8_planner import SampledSupervisor as Original
from .r9_planner import SampledSupervisor as Optimized
class TimedSupervisor:
    def __init__(self,chart,cfg):
        self.cfg=cfg;self.inner=(Optimized if cfg.get('optimized') else Original)(chart,cfg)
        self.pending=None;self.timeline=[];self.events=[];self.predictions=[];self.log=[]
    @property
    def base(self):return self.inner.base
    @property
    def goal_events(self):return self.inner.goal_events
    def plan(self,p,heading,velocity,current,goal,t,obs,*extra):
        if self.pending is not None:
            task=self.pending
            if t<task['ready']:return current
            self.pending=None
            if task['drop']:
                task['record']['status']='deadline_drop' if task['record']['deadline_overrun'] else 'age_drop';self.inner.held=None;self.inner.until=0;self.inner.next_plan=t+1
                return current
            task['record'].update(status='delivered',reference_apply=t+1)
            self.inner.until=t+1+self.cfg.get('period',15) if self.inner.held is not None else 0
            self.inner.next_plan=t+1+self.cfg.get('period',15)
            self.events.extend([dict(e,selected_at=e['time'],time=t+1) for e in task['events']])
            return task['target']
        n=len(self.inner.predictions);ne=len(self.inner.events);start=time.perf_counter()
        result=self.inner.plan(p,heading,velocity,current,goal,t,obs,*extra)
        wall=time.perf_counter()-start
        if len(self.inner.predictions)==n:return result
        prediction=self.inner.predictions[-1];self.predictions.append(prediction)
        newevents=self.inner.events[ne:]
        slot=self.cfg.get('slot');latency=max(1,math.ceil(wall)) if slot is None else int(slot)
        overrun=slot is not None and wall>slot
        drop=overrun or latency+1>self.cfg.get('max_age',60)
        if drop:latency=math.ceil(wall)
        record=dict(observation_time=t,plan_start=t,measured_wall=wall,plan_ready=t+wall,delivery_boundary=t+latency,reference_apply=None,status='pending',selected=prediction['selected'],target=list(result),deadline_overrun=overrun)
        self.timeline.append(record)
        self.pending=dict(ready=t+latency,target=result,events=newevents,record=record,drop=drop)
        return current
    def close(self):
        if self.pending:self.pending['record']['status']='task_end_drop'
        self.inner.close()
