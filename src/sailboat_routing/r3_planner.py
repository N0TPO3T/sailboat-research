"""R3 causal own-clearance intervention around unchanged R1/Relay planners.
No wind, simulator, future state, controller mutation or online physics rollout.
"""
from dataclasses import dataclass, replace
from collections import deque
import math
from .planner import PlannerInput, PlannerDecision
from .r1_planner import RouteWaypointPlanner, R1Config
from .r2_planner import RelayPlanner, RelayConfig

@dataclass(frozen=True)
class RiskConfig:
    base: str = "r1"
    margin: float = 80.
    threshold: float = 60.
    closing_gate: bool = False
    closing_speed: float = .05
    cooldown: float = 20.
    response: str = "bypass"
    relay_handoff: float = 100.
    relay_trigger: float = 80.

class RiskManagedPlanner:
    def __init__(self, chart, config=None, mode="geometry_only"):
        self.static_map=chart;self.config=config or RiskConfig()
        cfg=self.config
        if mode!="geometry_only":raise ValueError("R3 has no wind input branch")
        if cfg.base not in ("r1","relay") or cfg.response not in ("bypass","replan_only","none"):raise ValueError("Unknown R3 mechanism")
        self.base=(RouteWaypointPlanner(chart,R1Config(margin=cfg.margin)) if cfg.base=="r1" else
                   RelayPlanner(chart,RelayConfig(margin=cfg.margin,handoff=cfg.relay_handoff,trigger_clearance=cfg.relay_trigger)))
        self.motion=deque(maxlen=11);self.last_attempt=-math.inf;self.log=[]
    def plan(self,v):
        if type(v) is not PlannerInput:raise TypeError("Explicit visible input required")
        t=v.simulation_time;p=tuple(map(float,v.position_xy));cfg=self.config
        if self.motion and t<self.motion[-1][0]:raise ValueError("Nonmonotonic time")
        if not self.motion or t>self.motion[-1][0]:self.motion.append((t,p))
        own=math.inf;closest=None;closing=None;trigger=False;risk_obstacles=[]
        for i,o in enumerate(self.static_map.obstacles):
            clear=math.dist(p,o.center_xy)-o.entity_radius-o.safety_buffer
            speed=None
            if len(self.motion)==11:
                ot,op=self.motion[0];dt=t-ot
                if dt>0:speed=(math.dist(op,o.center_xy)-math.dist(p,o.center_xy))/dt
            if clear<own:own=clear;closest=i;closing=speed
            if clear<cfg.threshold and (not cfg.closing_gate or (speed is not None and speed>cfg.closing_speed)):
                trigger=True;risk_obstacles.append(dict(index=i,clearance=clear,closing_speed=speed))
        attempt=bool(trigger and v.current_goal_xy is not None and t-self.last_attempt>=cfg.cooldown and cfg.response!="none")
        old_cfg=self.base.config
        try:
            if attempt:
                self.last_attempt=t
                if cfg.base=="r1":
                    self.base.config=replace(old_cfg,period=0.,**(dict(hold=0.,improvement=0.) if cfg.response=="bypass" else {}))
                    decision=self.base.plan(v)
                elif cfg.response=="bypass":
                    # Relay selection depends on current only through its hold gate.
                    # None forces route recomputation; actual controller target/history stay unchanged.
                    decision=self.base.plan(replace(v,current_goal_xy=None))
                else:decision=self.base.plan(v)
            else:decision=self.base.plan(v)
        finally:self.base.config=old_cfg
        changed=decision.target_xy!=v.current_goal_xy
        if trigger or attempt or changed or t%10==0:
            self.log.append(dict(time=t,position=p,own_clearance=None if math.isinf(own) else own,nearest_obstacle=closest,
                closing_speed=closing,risk_obstacles=risk_obstacles,risk_detected=trigger,attempt=attempt,old_target=v.current_goal_xy,
                target=decision.target_xy,changed=changed,base_reason=decision.reason,
                response=cfg.response,base=cfg.base))
        reason=("risk_"+cfg.response+":"+decision.reason) if attempt else decision.reason
        return PlannerDecision(decision.target_xy,decision.candidates,reason,False)
