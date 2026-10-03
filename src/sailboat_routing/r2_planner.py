"""R2 development: frozen-R1 radial ablation and simple visible-route relay.
Radial500Planner copies fa6fecd plan logic, changing only the radial lengths.
The original r1_planner.py is deliberately unchanged.
"""
from dataclasses import dataclass, replace
from collections import deque
import math
from .planner import (StaticMap, PlannerDecision, CandidateScore, PlannerInput,
                      NoRouteError, NoLocalTargetError, distance, angle_difference)
from .metrics import segment_circle_clearance

from .r1_planner import R1Config

class Radial500Planner:
    offsets_override=None
    turn_weight=15.0
    change_weight=0.04
    handoff_distance=40.0
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
        valid=current is not None and (distance(p,current)>self.handoff_distance or current==goal) and distance(p,current)<=550 and chart.segment_clear(p,current)
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
        offsets=self.offsets_override if self.offsets_override is not None else (range(-12,13) if cfg.wide_candidates else (-1,0,1))
        for length in (500.,):
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
            turn=self.turn_weight*abs(angle_difference(a,v.heading_rad))
            change=self.change_weight*distance(q,current) if valid else 0.
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

class ForwardPlanner(Radial500Planner):
    """Route vertices, incumbent and one forward 500m radial candidate."""
    offsets_override=(0,)

class RouteCostPlanner(ForwardPlanner):
    """Forward candidates and inherited switching, with route cost alone."""
    turn_weight=0.0
    change_weight=0.0

class NoChangePlanner(ForwardPlanner):
    """Keep heading cost; remove only the displacement cost of switching."""
    change_weight=0.0

class EarlyHandoffPlanner(ForwardPlanner):
    """Retire non-final incumbent within 100m; keep necessary route corners."""
    handoff_distance=100.0

@dataclass(frozen=True)
class RelayConfig:
    margin: float = 80.0
    lookahead: float = 500.0
    handoff: float = 40.0
    trigger_clearance: float = 20.0
    maximum_distance: float = 550.0
    prediction_horizon: float = 0.0
    prediction_guard: float = 40.0

class RelayPlanner:
    """One visible route target, held until handoff or geometric risk.
    No wind, candidate scoring, environment query or altered control timing.
    """
    def __init__(self, chart, config=None, mode="geometry_only"):
        self.static_map=chart; self.config=config or RelayConfig(); self.log=[]
        self.last_time=-math.inf; self.last_scores=(); self.motion=deque(maxlen=11)
        if mode!="geometry_only": raise ValueError("Relay has no wind branch")

    def plan(self, v):
        if type(v) is not PlannerInput: raise TypeError("Explicit visible input required")
        if v.simulation_time<self.last_time: raise ValueError("Nonmonotonic time")
        self.last_time=v.simulation_time
        p=tuple(map(float,v.position_xy)); goal=v.route[-1]; current=v.current_goal_xy
        chart=self.static_map;cfg=self.config
        if not self.motion or v.simulation_time>self.motion[-1][0]: self.motion.append((v.simulation_time,p))
        if not chart.point_clear(p): raise NoRouteError("Current position outside original safe map")
        own=segment_circle_clearance(p,p,chart.obstacles)["safety_m"]
        chord=segment_circle_clearance(p,current,chart.obstacles)["safety_m"] if current else -math.inf
        valid=current is not None and distance(p,current)<=cfg.maximum_distance and chart.segment_clear(p,current)
        near=valid and current!=goal and distance(p,current)<=cfg.handoff
        risk=chord<min(cfg.trigger_clearance,max(0.,own-5.))
        predicted_clearance=None;velocity=None;forecast=None
        if cfg.prediction_horizon>0 and len(self.motion)==11:
            old_t,old_p=self.motion[0];dt=v.simulation_time-old_t
            velocity=((p[0]-old_p[0])/dt,(p[1]-old_p[1])/dt)
            forecast=(p[0]+cfg.prediction_horizon*velocity[0],p[1]+cfg.prediction_horizon*velocity[1])
            predicted_clearance=segment_circle_clearance(p,forecast,chart.obstacles)["safety_m"]
        predictive_risk=predicted_clearance is not None and predicted_clearance<cfg.prediction_guard
        if valid and not near and not risk and not predictive_risk:
            return PlannerDecision(current,self.last_scores,"relay_hold",False)
        reason="initial" if current is None else "invalid" if not valid else "risk" if risk else "prediction" if predictive_risk else "handoff"
        endpoint=min(own,segment_circle_clearance(goal,goal,chart.obstacles)["safety_m"])
        margin=min(cfg.margin,max(0.,endpoint-5.))
        planned=replace(chart,obstacles=tuple(replace(o,safety_buffer=o.safety_buffer+margin) for o in chart.obstacles))
        fallback=False
        try:route=planned.route(p,goal)
        except NoRouteError:
            planned=chart;margin=0.;fallback=True;route=chart.route(p,goal)
        # Walk up to lookahead along the route. Use the furthest *visible* point
        # encountered; do not cut an occluded turn or extrapolate beyond the goal.
        target=goal if len(route)==1 else None;walked=0.
        for a,b in zip(route,route[1:]):
            length=distance(a,b);advance=min(length,max(0.,cfg.lookahead-walked))
            q=b if advance==length else (a[0]+(b[0]-a[0])*advance/length,a[1]+(b[1]-a[1])*advance/length)
            if distance(p,q)>1e-8 and planned.segment_clear(p,q): target=q
            walked+=length
            if walked>=cfg.lookahead:break
        if target is None:raise NoLocalTargetError("No visible forward route point")
        remaining=sum(distance(a,b) for a,b in zip(route,route[1:]))
        self.last_scores=(CandidateScore(target,remaining,0.,0.,0.,remaining),)
        self.log.append({"time":v.simulation_time,"position":p,"old_target":current,
            "target":target,"reason":reason,"margin":margin,"fallback":fallback,
            "route":route,"own_clearance":own,"old_chord_clearance":chord,
            "geometric_risk":risk,"predictive_risk":predictive_risk,
            "prediction_clearance":predicted_clearance,"velocity":velocity,"forecast":forecast})
        return PlannerDecision(target,self.last_scores,reason,False)
