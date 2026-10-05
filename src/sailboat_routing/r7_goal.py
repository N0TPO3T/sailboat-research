"""Temporary mission-goal relay when a moving vessel occupies the final goal.
Uses current geometry only; staging circle is not a physical orbit prediction.
"""
import math
from dataclasses import replace
import numpy as np
from .r7_dynamic import EncounterSupervisor,circles,SAFE
from .metrics import segment_circle_clearance
from .planner import NoRouteError

class GoalRelaySupervisor(EncounterSupervisor):
    def __init__(self,chart,config):
        super().__init__(chart,config);self.staging=None;self.goal_events=[]
    def plan(self,p,heading,velocity,current,goal,t,obs):
        p=np.asarray(p,float);goal=np.asarray(goal,float)
        chart=replace(self.chart,obstacles=self.chart.obstacles+circles(obs))
        goal_gap=segment_circle_clearance(goal,goal,circles(obs))['safety_m']
        margin=self.base.config.margin;handoff=self.base.config.handoff
        distance=float(np.linalg.norm(goal-p));toward=float(np.asarray(velocity)@((goal-p)/max(distance,1e-9)))
        arrival=distance/toward if toward>.1 else math.inf
        windows=[]
        for o in obs:
            if not o['valid']:continue
            r=np.asarray(o['position'])-goal;w=np.asarray(o['velocity']);a=float(w@w);b=float(r@w);c=float(r@r)-(o['entity_radius']+o['safety_buffer'])**2
            if a<1e-10:
                if c<=0:windows.append((0.,math.inf))
                continue
            disc=b*b-a*c
            if disc>=0:
                enter=(-b-math.sqrt(disc))/a;leave=(-b+math.sqrt(disc))/a
                if leave>=0:windows.append((max(0.,enter),leave))
        slack=30. # measured order-of-magnitude response allowance, not a bound
        overlaps=math.isfinite(arrival) and any(arrival+slack>=a and arrival-slack<=b for a,b in windows)
        gate=overlaps or goal_gap<=0 or not self.cfg.get('goal_time_gate',True)
        if self.staging is None and goal_gap<=margin and gate:
            self.staging={};self.goal_events.append(dict(time=t,event='goal_planning_domain_blocked',goal_margin=goal_gap,nominal_arrival=arrival if math.isfinite(arrival) else None,occupancy_windows=windows,time_gate=self.cfg.get('goal_time_gate',True)))
        if self.staging is not None and goal_gap>margin:
            self.staging=None;self.active=None;current=None
            self.goal_events.append(dict(time=t,event='goal_released',goal_margin=goal_gap))
        if self.staging is not None:
            old=self.staging.get('goal')
            if old is None or np.linalg.norm(p-old)<handoff or not chart.segment_clear(tuple(p),tuple(old)):
                radius=SAFE+margin+handoff;options=[]
                for k in range(8):
                    q=goal+radius*np.array([math.cos(k*math.pi/4),math.sin(k*math.pi/4)])
                    if np.linalg.norm(q-p)<2*handoff or not chart.segment_clear(tuple(p),tuple(q)):continue
                    if segment_circle_clearance(q,q,chart.obstacles)['safety_m']<margin:continue
                    angle=math.atan2(q[1]-p[1],q[0]-p[0]);turn=abs(math.atan2(math.sin(angle-heading),math.cos(angle-heading)))
                    options.append((float(np.linalg.norm(q-p))+80*turn,q))
                if not options:raise NoRouteError('No feasible temporary goal relay')
                _,q=min(options,key=lambda a:a[0]);self.staging['goal']=q.tolist();self.active=None;current=None
                self.goal_events.append(dict(time=t,event='staging_reference',target=q.tolist(),goal_margin=goal_gap))
            goal=np.asarray(self.staging['goal'])
        # Actual final-goal arrival test remains unchanged in the physical runner.
        return super().plan(p,heading,velocity,current,goal,t,obs)
