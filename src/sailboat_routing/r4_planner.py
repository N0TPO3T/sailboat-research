"""R4 causal execution intervention around the unchanged geometric Relay.

Only PlannerInput (current pose, target, static route, clock) is accepted.
No branch observer, wind field, actor, or future state enters this module.
"""
from dataclasses import dataclass, replace
import math
from .r2_planner import RelayPlanner, RelayConfig
from .planner import PlannerDecision, distance, NoRouteError, NoLocalTargetError
from .metrics import segment_circle_clearance


@dataclass(frozen=True)
class ExecutionConfig(RelayConfig):
    response_horizon: float = 60.0
    risk_guard: float = 80.0
    response_hold: float = 60.0
    progress_gate: bool = True
    intervention: str = "away"
    target_grace: float = 0.0


class ExecutionPlanner:
    def __init__(self, chart, config=None, mode="geometry_only"):
        self.config = config or ExecutionConfig()
        self.base = RelayPlanner(chart, self.config, mode)
        self.log = []
        self.last_attempt = -math.inf
        self.escape_target = None
        self.hold_until = -math.inf
        self.observed_target = None
        self.target_since = 0.0
        self.grace_logged = False

    def plan(self, v):
        ordinary = self.base.plan(v)
        cfg = self.config
        chart = self.base.static_map
        p, current, t = v.position_xy, v.current_goal_xy, v.simulation_time
        if current != self.observed_target:
            self.observed_target = current
            self.target_since = t
            self.grace_logged = False
        if current is None or len(self.base.motion) < 11:
            return ordinary
        # Keep the chosen command long enough to observe a response, unless its
        # original-map segment becomes invalid or it reaches normal handoff.
        if (self.escape_target is not None and current == self.escape_target
                and t < self.hold_until and cfg.handoff < distance(p, current) <= cfg.maximum_distance
                and chart.segment_clear(p, current)):
            return PlannerDecision(current, (), "execution_response_hold", False)
        if t - self.last_attempt < cfg.response_horizon:
            return ordinary
        old_t, old_p = self.base.motion[0]
        dt = t - old_t
        velocity = ((p[0]-old_p[0])/dt, (p[1]-old_p[1])/dt)
        d = distance(p, current)
        if d < 1e-8:
            return ordinary
        progress = sum(velocity[k]*(current[k]-p[k])/d for k in (0, 1))
        clearance = lambda a, b: segment_circle_clearance(a, b, chart.obstacles)["safety_m"]
        own, previous = clearance(p, p), clearance(old_p, old_p)
        forecast = tuple(p[k] + cfg.response_horizon*velocity[k] for k in (0, 1))
        predicted = clearance(p, forecast)
        risk = (own < cfg.margin and own < previous and predicted < cfg.risk_guard
                and (not cfg.progress_gate or progress <= 0.0))
        if not risk:
            return ordinary
        target_age = t - self.target_since
        # Negative progress immediately after a new target can be a transient
        # manoeuvre. Give it time, unless already inside the intervention guard.
        if target_age < cfg.target_grace and own >= cfg.risk_guard:
            if not self.grace_logged:
                self.log.append(dict(event="response_grace", time=t, position=p,
                    current_target=current, ordinary_target=ordinary.target_xy,
                    target=None, changed=False, target_age=target_age,
                    progress_mps=progress, own_clearance=own, previous_clearance=previous,
                    velocity=velocity, forecast=forecast, predicted_clearance=predicted))
                self.grace_logged = True
            return ordinary
        self.last_attempt = t
        q = None
        if cfg.intervention == "route":
            try:
                q = RelayPlanner(chart, cfg).plan(replace(v, current_goal_xy=None)).target_xy
            except (NoRouteError, NoLocalTargetError):
                # A failed optional alternative does not invalidate an already
                # valid ordinary proposal; use the same fallback as outward.
                pass
        elif cfg.intervention == "away":
            obstacle = min(chart.obstacles, key=lambda o: distance(p, o.center_xy)-o.exclusion_radius)
            radius = distance(p, obstacle.center_xy)
            for length in (500.0, 250.0):
                candidate = tuple(p[k]+length*(p[k]-obstacle.center_xy[k])/radius for k in (0, 1))
                if not chart.segment_clear(p, candidate):
                    continue
                try:
                    chart.route(candidate, v.route[-1])
                except NoRouteError:
                    continue
                q = candidate
                break
        else:
            raise ValueError("Unknown intervention")
        changed = q is not None and distance(q, ordinary.target_xy) > 1e-6
        self.log.append(dict(event="intervention_attempt", time=t, position=p, current_target=current,
            ordinary_target=ordinary.target_xy, target=q, intervention=cfg.intervention,
            progress_mps=progress, own_clearance=own, previous_clearance=previous,
            velocity=velocity, forecast=forecast, predicted_clearance=predicted,
            changed=changed, hold_until=t+cfg.response_hold, target_age=target_age))
        if not changed:
            return ordinary
        self.escape_target = q
        self.hold_until = t + cfg.response_hold
        return PlannerDecision(q, (), "execution_"+cfg.intervention, False)
