"""R7 timestamped vessel observations and CPA encounter reference supervision.
Adaptation of Eriksen et al. (2020), sec6.2, not its MPC or safety claims.
Environment target functions are intentionally separate from planner inputs.
"""
import math
from dataclasses import replace
import numpy as np
from .planner import CircleObstacle, PlannerInput
from .r2_planner import RelayPlanner, RelayConfig
from .r6_controller import ObstacleFrame
from .frames import LocalFrame, reencode_controller

ENTITY=20.0 # own circumscribed radius5 + target radius15; counted ONCE
BUFFER=60.0
SAFE=ENTITY+BUFFER

def target_truth(spec,t):
    # Piecewise constant velocity; turns allowed only on integer step boundaries.
    p=np.asarray(spec['position'],float).copy();v=np.asarray(spec['velocity'],float);last=0.
    for turn in spec.get('turns',[]):
        if turn['time']>t:break
        p+=v*(turn['time']-last);last=turn['time'];v=np.asarray(turn['velocity'],float)
    return p+v*(t-last),v

def observe(specs,t,own,range_m=1000.):
    rows=[]
    for spec in specs:
        p,v=target_truth(spec,t)
        if np.linalg.norm(p-own)<=range_m:
            rows.append(dict(id=spec['id'],time=float(t),position=p.tolist(),velocity=v.tolist(),valid=True,
                             entity_radius=ENTITY,safety_buffer=BUFFER,vessel_class='motor'))
    return rows

def circles(obs):
    return tuple(CircleObstacle(tuple(o['position']),o['entity_radius'],o['safety_buffer']) for o in obs if o['valid'])

def relative_minimum(p0,p1,q0,q1):
    r=np.asarray(p0)-q0;d=np.asarray(p1)-q1-r
    f=float(np.clip(-r@d/(d@d),0,1)) if d@d>1e-12 else 0.
    return float(np.linalg.norm(r+f*d)),f

def cpa(p,v,q,w):
    r=np.asarray(q)-p;u=np.asarray(w)-v
    tau=float(-r@u/(u@u)) if u@u>1e-10 else 0.
    return tau,float(np.linalg.norm(r+max(0.,tau)*u))

class HistoricalFrame:
    # frames.reencode_controller traverses states in chronological order exactly once.
    def __init__(self,base,static,observations):self.base=base;self.static=static;self.observations=observations;self.i=0
    def encode(self,raw,previous=None):
        obs=self.observations[self.i];self.i+=1
        return ObstacleFrame(self.base,self.static+circles(obs),'boundary40').encode(raw,previous)

def encode(base,static,obs,raw,previous=None):
    return ObstacleFrame(base,static+circles(obs),'boundary40').encode(raw,previous)

def replay(policy,base,static,observations,history,commands):
    assert len(observations)==len(history)==len(commands)+1
    return reencode_controller(policy,HistoricalFrame(base,static,observations),history,commands)

class EncounterSupervisor:
    def __init__(self,chart,config):
        self.chart=chart;self.cfg=config;self.base=RelayPlanner(chart,RelayConfig(margin=120,lookahead=500,handoff=100,trigger_clearance=80))
        self.active=None;self.log=[];self.events=[]
    def plan(self,p,heading,velocity,current,goal,t,obs):
        cfg=self.cfg;mode=cfg.get('mode','current');p=np.asarray(p,float);velocity=np.asarray(velocity,float)
        dynamic=replace(self.chart,obstacles=self.chart.obstacles+circles(obs));self.base.static_map=dynamic
        visible=PlannerInput(tuple(p),float(heading),current,(tuple(p),tuple(goal)),float(t),None)
        risks=[]
        for o in obs:
            tau,d=cpa(p,velocity,np.asarray(o['position']),np.asarray(o['velocity']))
            risks.append(dict(id=o['id'],tcpa=tau,dcpa=d,distance=float(np.linalg.norm(p-o['position']))))
        selected=None;reason='relay';entry=None
        if mode!='current' and t>=10:
            byid={o['id']:o for o in obs}
            if self.active is not None:
                a=self.active;o=byid.get(a['id']);release=False
                if o is not None:
                    q=np.asarray(o['position']);w=np.asarray(o['velocity']);r=p-q
                    tau,d=cpa(p,velocity,q,w)
                    if mode=='no_commit':release=not(0<tau<cfg.get('horizon',180) and d<SAFE+cfg.get('guard',100))
                    else:
                        past=float(r@np.asarray(a.get('overtaken_axis',a['axis'])))>SAFE+100 if a['overtaking'] else float(r@(velocity-w))>0
                        release=bool(past and np.linalg.norm(r)>SAFE+150)
                    if release:
                        self.events.append(dict(time=t,event='release',id=a['id'],distance=float(np.linalg.norm(r)),past_projection=float(r@np.asarray(a.get('overtaken_axis',a['axis'])))));self.active=None;visible=replace(visible,current_goal_xy=None)
                if self.active is not None:
                    selected=np.asarray(a['target']);reason='encounter_hold'
                    if np.linalg.norm(selected-p)<100:
                        axis=np.asarray(a['axis']);normal=np.array([-axis[1],axis[0]])
                        q=np.asarray(o['position']) if o else np.asarray(a['anchor'])
                        selected=p+axis*400
                        selected+=normal*(a['side']*cfg.get('offset',240)-float((selected-q)@normal))
                        if dynamic.segment_clear(tuple(p),tuple(selected)):
                            a['target']=selected.tolist();reason='encounter_extend'
                        else:selected=np.asarray(a['target']);reason='encounter_blocked_hold'
            if self.active is None:
                dangerous=[r for r in risks if 0<r['tcpa']<cfg.get('horizon',180) and r['dcpa']<SAFE+cfg.get('guard',100)]
                if dangerous:
                    risk=min(dangerous,key=lambda r:r['tcpa']);o=byid[risk['id']];q=np.asarray(o['position']);w=np.asarray(o['velocity'])
                    axis=(np.asarray(goal)-p);axis/=np.linalg.norm(axis);normal=np.array([-axis[1],axis[0]])
                    anchor=q+w*min(risk['tcpa'],cfg.get('horizon',180));choices=[]
                    for side in (-1,1):
                        target=anchor+axis*180+side*normal*cfg.get('offset',240)
                        # A reference is a waypoint, NOT a predicted actual vessel course.
                        if dynamic.segment_clear(tuple(p),tuple(target)) and self.chart.point_clear(tuple(target)):
                            turn=abs(math.atan2(math.sin(math.atan2(*(target-p)[::-1])-heading),math.cos(math.atan2(*(target-p)[::-1])-heading)))
                            cost=np.linalg.norm(target-p)+np.linalg.norm(np.asarray(goal)-target)+80*turn
                            choices.append((float(cost),side,target))
                    if choices:
                        _,side,selected=min(choices,key=lambda x:x[0]);overtaking=bool(np.linalg.norm(w)>0.1 and (p-q)@w/np.linalg.norm(w)<-math.cos(math.radians(67.5))*np.linalg.norm(p-q))
                        self.active=dict(id=o['id'],axis=axis.tolist(),anchor=anchor.tolist(),side=side,target=selected.tolist(),overtaking=overtaking,overtaken_axis=(w/max(np.linalg.norm(w),1e-9)).tolist())
                        entry=dict(time=t,event='enter',**risk,target=selected.tolist(),side=side,overtaking=overtaking,velocity=velocity.tolist(),position=p.tolist(),target_observation=o)
                        self.events.append(entry);reason='encounter_enter'
        if selected is None:selected=np.asarray(self.base.plan(visible).target_xy)
        self.log.append(dict(time=t,position=p.tolist(),velocity=velocity.tolist(),observations=obs,risks=risks,reason=reason,target=selected.tolist(),active_id=self.active['id'] if self.active else None))
        return tuple(map(float,selected))
