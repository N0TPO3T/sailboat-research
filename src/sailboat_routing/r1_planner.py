"""R1 route-aware targets. Only map, position/heading history and optional local wind."""
from dataclasses import dataclass, replace
from collections import deque
import math
from .planner import (StaticMap, PlannerDecision, CandidateScore, PlannerInput,
                      NoRouteError, NoLocalTargetError, distance, angle_difference)
from .metrics import segment_circle_clearance

@dataclass(frozen=True)
class R1Config:
    margin: float = 80.0
    period: float = 10.0
    hold: float = 20.0
    improvement: float = 15.0
    history_gain: float = 0.0
    wind_weight: float = 0.0
    wide_candidates: bool = True

class RouteWaypointPlanner:
    def __init__(self, chart, config=None, mode="geometry_only"):
        self.static_map=chart; self.config=config or R1Config(); self.mode=mode
        self.previous=deque(maxlen=21); self.last_plan=-math.inf; self.last_switch=-math.inf
        self.last_scores=(); self.log=[]; self.history_target=None

    def plan(self, v):
        if type(v) is not PlannerInput: raise TypeError("Explicit visible input required")
        p=tuple(map(float,v.position_xy)); goal=v.route[-1]; t=v.simulation_time; cfg=self.config
        if self.previous and t<self.previous[-1][0]: raise ValueError("Nonmonotonic time")
        if v.current_goal_xy != self.history_target:
            self.previous.clear(); self.history_target=v.current_goal_xy
        if not self.previous or t>self.previous[-1][0]: self.previous.append((t,p))
        chart=self.static_map; current=v.current_goal_xy
        if not chart.point_clear(p): raise NoRouteError("Current position outside original safe map")
        own_clear=segment_circle_clearance(p,p,chart.obstacles)["safety_m"]
        cur_clear=segment_circle_clearance(p,current,chart.obstacles)["safety_m"] if current else -math.inf
        valid=current is not None and (distance(p,current)>40 or current==goal) and distance(p,current)<=550 and chart.segment_clear(p,current)
        urgent=not valid or cur_clear<min(20.,max(0.,own_clear-5.))
        if not urgent and t-self.last_plan<cfg.period:
            return PlannerDecision(current,self.last_scores,"replan_period",False)
        # Extra planning margin is capped at the available start/goal clearance.
        # Original safety geometry is immutable; inability to inflate is not unsafe permission.
        endpoint_clear=min(own_clear,segment_circle_clearance(goal,goal,chart.obstacles)["safety_m"])
        margin=min(cfg.margin,max(0.,endpoint_clear-5.))
        planned=replace(chart,obstacles=tuple(replace(o,safety_buffer=o.safety_buffer+margin) for o in chart.obstacles))
        try: route=planned.route(p,goal)
        except NoRouteError:
            planned=chart; margin=0.; route=chart.route(p,goal)
        tail=[0.]*len(route)
        for i in range(len(route)-2,-1,-1): tail[i]=tail[i+1]+distance(route[i],route[i+1])
        desired=math.atan2(route[1][1]-p[1],route[1][0]-p[0])
        # Observed course bias relative to the actual previous target, never wind truth.
        bias=0.
        if cfg.history_gain and len(self.previous)>10 and valid:
            a,b=self.previous[0],self.previous[-1]
            if distance(a[1],b[1])>5:
                course=math.atan2(b[1][1]-a[1][1],b[1][0]-a[1][0])
                bearing=math.atan2(current[1]-a[1][1],current[0]-a[1][0])
                bias=max(-.5,min(.5,angle_difference(course,bearing)))*cfg.history_gain
        targets=[]
        if valid: targets.append(current)
        for q in route[1:]:
            if (q==goal or distance(p,q)>15) and 0<distance(p,q)<=500 and planned.segment_clear(p,q): targets.append(q)
        offsets=range(-12,13) if cfg.wide_candidates else (-1,0,1)
        for length in ((500.,300.,150.) if cfg.wide_candidates else (500.,)):
            for k in offsets:
                angle=desired+k*math.pi/12
                targets.append((p[0]+length*math.cos(angle),p[1]+length*math.sin(angle)))
        scores=[];use_wind=self.mode!='geometry_only' and v.wind is not None and v.wind.valid
        for q in targets:
            if not planned.segment_clear(p,q): continue
            if any(distance(q,s.target_xy)<1e-5 for s in scores):continue
            connections=[distance(q,r)+tail[i] for i,r in enumerate(route[1:],1) if planned.segment_clear(q,r)]
            if not connections:continue
            d=distance(p,q); a=math.atan2(q[1]-p[1],q[0]-p[0])
            remaining=d+min(connections)
            turn=15*abs(angle_difference(a,v.heading_rad))
            change=.04*distance(q,current) if valid else 0.
            wind=cfg.wind_weight*min(d,500)*max(0.,math.cos(a-v.wind.angle_world_rad-math.pi))**2 if use_wind else 0.
            # Directional compensation is a cost, so the geometric controls use identical candidates.
            history=100.*(abs(angle_difference(a,desired-bias))-abs(angle_difference(a,desired))) if cfg.history_gain else 0.
            scores.append(CandidateScore(q,remaining,wind,turn,change,remaining+wind+turn+change+history))
        if not scores:raise NoLocalTargetError("Expanded route-aware candidate set empty")
        best=min(scores,key=lambda s:s.total); incumbent=next((s for s in scores if s.target_xy==current),None)
        reason="selected"
        if incumbent and not urgent:
            if t-self.last_switch<cfg.hold:best=incumbent;reason="minimum_hold"
            elif best.total>=incumbent.total-cfg.improvement:best=incumbent;reason="hysteresis"
        if best.target_xy!=current:self.last_switch=t
        self.last_plan=t;self.last_scores=tuple(scores)
        self.log.append({"time":t,"margin":margin,"bias":bias,"candidate_count":len(scores),"reason":reason,"target":best.target_xy})
        return PlannerDecision(best.target_xy,tuple(scores),reason,bool(use_wind))
