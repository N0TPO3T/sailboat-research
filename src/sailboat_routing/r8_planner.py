"""Sampled GVO-style waypoint/feedback controls; no privileged inputs."""
import copy,math,time
from dataclasses import replace
import numpy as np
from .r7_dynamic import EncounterSupervisor,circles,SAFE
from .planner import NoRouteError,NoLocalTargetError
from .metrics import segment_circle_clearance
from .r8_model import CausalModel

class AvailabilityRelay(EncounterSupervisor):
    """Shared reactive baseline: temporary occupied endpoint is not permanent failure."""
    def __init__(self,chart,config):super().__init__(chart,dict(config,mode='current'));self.blocked=False;self.goal_events=[]
    def plan(self,p,heading,velocity,current,goal,t,obs):
        chart=replace(self.chart,obstacles=self.chart.obstacles+circles(obs));occupied=not chart.point_clear(tuple(goal))
        if not occupied:
            if self.blocked:current=None;self.goal_events.append(dict(time=t,event='endpoint_available'))
            self.blocked=False
            return super().plan(p,heading,velocity,current,goal,t,obs)
        if not self.blocked:self.goal_events.append(dict(time=t,event='endpoint_unavailable'))
        self.blocked=True
        if current is not None and np.linalg.norm(np.asarray(current)-p)>100 and chart.segment_clear(tuple(p),tuple(current)) and chart.point_clear(tuple(current)):
            return tuple(current)
        choices=[]
        for k in range(8):
            q=np.asarray(goal)+305*np.array([math.cos(k*math.pi/4),math.sin(k*math.pi/4)])
            if np.linalg.norm(q-p)<200 or not chart.segment_clear(tuple(p),tuple(q)):continue
            if segment_circle_clearance(q,q,chart.obstacles)['safety_m']<120:continue
            angle=math.atan2(q[1]-p[1],q[0]-p[0]);turn=abs(math.atan2(math.sin(angle-heading),math.cos(angle-heading)))
            choices.append((np.linalg.norm(q-p)+80*turn,q))
        if not choices:raise NoRouteError('No feasible temporary availability reference')
        return tuple(min(choices,key=lambda x:x[0])[1])

class SampledSupervisor:
    def __init__(self,chart,config):
        self.chart=chart;self.cfg=config;self.base=AvailabilityRelay(chart,config);self.model=CausalModel();self.next_plan=10;self.held=None;self.until=0;self.predictions=[];self.events=[];self.log=[]
    @property
    def goal_events(self):return self.base.goal_events
    def plan(self,p,heading,velocity,current,goal,t,obs,history,commands,oh,frame,old_action,pending=()):
        if t<self.until:return tuple(self.held)
        incumbent=None if self.held is not None else current
        nominal=self.base.plan(p,heading,velocity,incumbent,goal,t,obs)
        nearby=any(o['valid'] and np.linalg.norm(np.asarray(o['position'])-p)<600 for o in obs)
        if t<self.next_plan or not nearby:
            if self.held is not None:
                self.events.append(dict(time=t,event='release',selected='nominal',target=list(nominal),reason='outside_prediction_range'));self.held=None
            return nominal
        begin=time.perf_counter();self.next_plan=t+self.cfg.get('period',15);self.model.estimate(history)
        H=self.cfg.get('horizon',60);guard=self.cfg.get('guard',30);hold=self.cfg.get('period',15)
        options=[('nominal',np.asarray(nominal),0)]
        if current is not None:options.append(('continue',np.asarray(current),hold))
        axis=math.atan2(nominal[1]-p[1],nominal[0]-p[0])
        for deg in [-90,-45,45,90]:options.append((f'turn{deg}',np.asarray(p)+350*np.array([math.cos(axis+math.radians(deg)),math.sin(axis+math.radians(deg))]),hold))
        evaluated=[]
        for name,q,duration in options:
            pred=self.model.rollout(history,commands,oh,frame,q,old_action,H,self.chart.obstacles,np.asarray(goal),copy.deepcopy(self.base),duration,pending,self.cfg.get('goal_delay',0))
            if self.cfg.get('ablation')=='unconditioned':
                if evaluated:pred=copy.deepcopy(evaluated[0]['prediction'])
            feasible=pred['valid'] and pred['min_margin']>=guard and not pred['integration_failed']
            cost=pred['terminal_distance']+(0 if name=='nominal' else 20)+(0 if name in ['nominal','continue'] else 10)
            evaluated.append(dict(name=name,target=q.tolist(),hold=duration,prediction=pred,feasible=feasible,cost=float(cost)))
            if name=='nominal' and feasible:break
        safe=[x for x in evaluated if x['feasible']]
        # Prefer ordinary feedback whenever it is predicted safe; intervene for safety only.
        if evaluated[0]['feasible']:selected=evaluated[0]
        elif safe:selected=min(safe,key=lambda x:x['cost'])
        else:
            complete=[x for x in evaluated if x['prediction']['valid'] and not x['prediction']['integration_failed']]
            selected=max(complete,key=lambda x:(x['prediction']['min_margin'],-x['cost'])) if complete else next((x for x in evaluated if x['name']=='continue'),evaluated[0])
        previous=self.held;self.held=None if selected['name']=='nominal' else selected['target'];self.until=t+hold if self.held is not None else 0
        event='ordinary' if self.held is None and previous is None else 'release' if self.held is None else 'enter' if previous is None else 'reevaluate'
        self.events.append(dict(time=t,event=event,selected=selected['name'],target=selected['target'],all_predicted_infeasible=not bool(safe)))
        self.predictions.append(dict(time=t,position=list(map(float,p)),wind_estimate=self.model.wind.tolist(),selected=selected['name'],candidates=evaluated,wall_seconds=time.perf_counter()-begin))
        return tuple(selected['target'])
    def close(self):self.model.close()
