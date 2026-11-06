"""Position-target adaptation of Jambak et al. (2026), doi:10.3390/drones10080578.

Preserves Eq13 tangent construction, Eq15 alignment/side bonus, and verbal
commitment/hysteresis structure in Sec5. No wind projection or source controller.
Unspecified source thresholds and position-target timing are explicit adaptations.
"""
from dataclasses import dataclass, replace
import math
from .r2_planner import RelayConfig, RelayPlanner
from .planner import PlannerInput, PlannerDecision, NoRouteError, distance
from .metrics import segment_circle_clearance


@dataclass(frozen=True)
class TangentConfig(RelayConfig):
    tangent_buffer: float = 12.0
    entry_clearance: float = 12.0
    exit_clearance: float = 18.0
    commitment_time: float = 60.0
    minimum_recovery_time: float = 60.0
    side_bonus: float = 0.05
    switch_improvement: float = 0.10
    update_period: float = 10.0
    target_length: float = 500.0
    hold_position: bool = False


def tangent_headings(p, obstacle, buffer):
    theta=math.atan2(obstacle.center_xy[1]-p[1],obstacle.center_xy[0]-p[0])
    radius=obstacle.exclusion_radius+buffer
    gamma=math.asin(min(1.,radius/distance(p,obstacle.center_xy)))
    return {-1:theta-gamma,1:theta+gamma}


class TangentSupervisor:
    def __init__(self, chart, config=None, mode='geometry_only'):
        self.config=config or TangentConfig();self.static_map=chart
        self.base=RelayPlanner(chart,self.config,mode);self.log=[]
        self.obstacle_index=None;self.side=None;self.side_since=-math.inf
        self.entered_at=-math.inf;self.last_update=-math.inf;self.last_time=-math.inf
        self.recovery_target=None

    def _clear(self,a,b):
        return segment_circle_clearance(a,b,self.static_map.obstacles)['safety_m']

    def _entry(self,p,nominal):
        # Source "relevance" is underspecified. Here: obstacle projects onto
        # the finite nominal leg, or the vessel is already within entry range.
        cfg=self.config;dx=nominal[0]-p[0];dy=nominal[1]-p[1]
        length=max(distance(p,nominal),1e-9);eligible=[]
        for i,o in enumerate(self.static_map.obstacles):
            own=distance(p,o.center_xy)-o.exclusion_radius
            along=((o.center_xy[0]-p[0])*dx+(o.center_xy[1]-p[1])*dy)/length
            relevant=(0<=along<=length and own<=cfg.lookahead) or own<=cfg.entry_clearance
            blocked=segment_circle_clearance(p,nominal,(o,))['safety_m']<=0
            if relevant and (own<=cfg.entry_clearance or blocked):eligible.append((own,i))
        return min(eligible)[1] if eligible else None

    def plan(self,v):
        if type(v) is not PlannerInput:raise TypeError('Visible input whitelist required')
        t=v.simulation_time;p=v.position_xy;current=v.current_goal_xy;cfg=self.config
        if t<self.last_time:raise ValueError('Nonmonotonic time')
        self.last_time=t
        if not self.static_map.point_clear(p):raise NoRouteError('Current position outside original safe map')
        active=self.obstacle_index is not None
        valid=current is not None and cfg.handoff<distance(p,current)<=cfg.maximum_distance and self.static_map.segment_clear(p,current)
        if active and valid and t-self.last_update<cfg.update_period:
            return PlannerDecision(current,(),'tangent_interval_hold',False)
        # A fresh nominal proposal during recovery cannot mistake the recovery
        # target for its own route target. Normal mode uses unchanged Relay.
        ordinary=self.base.plan(replace(v,current_goal_xy=None) if active else v)
        entry=self._entry(p,ordinary.target_xy)
        if not active:
            if entry is None:return ordinary
            self.obstacle_index=entry;self.entered_at=t;self.side=None
            self.log.append(dict(event='enter',time=t,position=p,obstacle=entry,
                                 nominal_target=ordinary.target_xy,own_clearance=self._clear(p,p)))
        else:
            o=self.static_map.obstacles[self.obstacle_index]
            own=distance(p,o.center_xy)-o.exclusion_radius
            restored=own>=cfg.exit_clearance or self._clear(p,ordinary.target_xy)>=cfg.exit_clearance
            if t-self.entered_at>=cfg.minimum_recovery_time and entry is None and restored:
                self.log.append(dict(event='exit',time=t,position=p,obstacle=self.obstacle_index,
                                     target=ordinary.target_xy,own_clearance=own))
                self.obstacle_index=None;self.side=None;self.recovery_target=None
                return ordinary
            if cfg.hold_position and valid and current==self.recovery_target:
                self.last_update=t
                return PlannerDecision(current,(),'tangent_position_hold',False)
        o=self.static_map.obstacles[self.obstacle_index]
        nominal=ordinary.target_xy;ng=max(distance(p,nominal),1e-9)
        g=((nominal[0]-p[0])/ng,(nominal[1]-p[1])/ng)
        candidates=[]
        for side,angle in tangent_headings(p,o,cfg.tangent_buffer).items():
            h=(math.cos(angle),math.sin(angle));q=tuple(p[k]+cfg.target_length*h[k] for k in (0,1))
            alignment=sum(h[k]*g[k] for k in (0,1));bonus=cfg.side_bonus if side==self.side else 0.
            valid_q=self.static_map.segment_clear(p,q);route_ok=False
            if valid_q:
                try:self.static_map.route(q,v.route[-1]);route_ok=True
                except NoRouteError:pass
            candidates.append(dict(side=side,angle_rad=angle,target=q,alignment=alignment,
                                   bonus=bonus,score=alignment+bonus,segment_valid=valid_q,route_valid=route_ok))
        feasible=[c for c in candidates if c['segment_valid'] and c['route_valid']]
        self.last_update=t
        if not feasible:
            self.log.append(dict(event='no_candidate',time=t,position=p,obstacle=self.obstacle_index,
                                 candidates=candidates,target=ordinary.target_xy))
            # No braking/hovering assumption. Resume baseline; no safety claim.
            self.obstacle_index=None;self.side=None;self.recovery_target=None
            return ordinary
        best=max(feasible,key=lambda c:c['score'])
        incumbent=next((c for c in feasible if c['side']==self.side),None)
        reason='best_alignment'
        if incumbent is not None and best['side']!=self.side:
            if t-self.side_since<cfg.commitment_time:best=incumbent;reason='side_dwell'
            elif best['score']-incumbent['score']<cfg.switch_improvement:best=incumbent;reason='side_deadband'
        if best['side']!=self.side:self.side_since=t
        self.side=best['side'];self.recovery_target=best['target']
        self.log.append(dict(event='target',time=t,position=p,obstacle=self.obstacle_index,
                             current_target=current,nominal_target=nominal,candidates=candidates,
                             selected_side=self.side,reason=reason,target=best['target'],
                             own_clearance=self._clear(p,p),entered_at=self.entered_at))
        return PlannerDecision(best['target'],(),'tangent_recovery',False)
