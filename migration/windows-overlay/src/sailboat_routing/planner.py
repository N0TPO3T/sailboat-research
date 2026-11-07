"""Deterministic static-map geometry and bounded local target selection.

No environment, wind field, or random generator enters this module.
"""
from dataclasses import dataclass
import heapq
import math

Point = tuple[float, float]


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle_difference(a: float, b: float) -> float:
    return (a - b + math.pi) % (2 * math.pi) - math.pi


@dataclass(frozen=True, slots=True)
class CircleObstacle:
    center_xy: Point
    entity_radius: float
    safety_buffer: float = 0.0

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (*self.center_xy, self.entity_radius, self.safety_buffer)):
            raise ValueError("Obstacle values must be finite")
        if self.entity_radius < 0 or self.safety_buffer < 0:
            raise ValueError("Entity radius and safety buffer must be nonnegative")

    @property
    def exclusion_radius(self):
        return self.entity_radius + self.safety_buffer


class NoRouteError(ValueError):
    """No map-valid geometric path exists at this grid resolution."""


class NoLocalTargetError(ValueError):
    """The bounded candidate set has no map-valid local target."""


@dataclass(frozen=True, slots=True)
class StaticMap:
    bounds: tuple[float, float, float, float]  # xmin, xmax, ymin, ymax
    obstacles: tuple[CircleObstacle, ...] = ()
    grid_resolution: float = 50.0

    def __post_init__(self):
        xmin, xmax, ymin, ymax = self.bounds
        if not all(math.isfinite(v) for v in (*self.bounds, self.grid_resolution)):
            raise ValueError("Map values must be finite")
        if xmin >= xmax or ymin >= ymax or self.grid_resolution <= 0:
            raise ValueError("Invalid bounds or grid resolution")

    def point_clear(self, p: Point) -> bool:
        xmin, xmax, ymin, ymax = self.bounds
        return (all(math.isfinite(v) for v in p) and xmin <= p[0] <= xmax
                and ymin <= p[1] <= ymax and all(
                    distance(p, o.center_xy) > o.exclusion_radius for o in self.obstacles))

    def segment_clear(self, a: Point, b: Point) -> bool:
        if not self.point_clear(a) or not self.point_clear(b):
            return False
        dx, dy = b[0] - a[0], b[1] - a[1]
        length2 = dx * dx + dy * dy
        for o in self.obstacles:
            t = 0.0 if length2 == 0 else max(0.0, min(1.0, (
                (o.center_xy[0] - a[0]) * dx + (o.center_xy[1] - a[1]) * dy) / length2))
            if distance((a[0] + t * dx, a[1] + t * dy), o.center_xy) <= o.exclusion_radius:
                return False
        return True

    def route(self, start: Point, goal: Point) -> tuple[Point, ...]:
        """8-connected A*, then greedy line-of-sight simplification.

        Grid nodes are internal; returned vertices are critical geometric turns,
        not a list of targets that the low-level controller must visit.
        """
        if not self.point_clear(start) or not self.point_clear(goal):
            raise NoRouteError("Start or final goal violates map constraints")
        if self.segment_clear(start, goal):
            return (start, goal) if start != goal else (start,)
        xmin, xmax, ymin, ymax = self.bounds
        step = self.grid_resolution
        nx, ny = math.floor((xmax - xmin) / step), math.floor((ymax - ymin) / step)
        def point(node):
            return (xmin + node[0] * step, ymin + node[1] * step)
        def connections(p):
            ix, iy = round((p[0] - xmin) / step), round((p[1] - ymin) / step)
            return tuple((x, y) for x in range(max(0, ix - 1), min(nx, ix + 1) + 1)
                         for y in range(max(0, iy - 1), min(ny, iy + 1) + 1)
                         if self.segment_clear(p, point((x, y))))
        starts, ends = connections(start), set(connections(goal))
        queue, costs, parents = [], {}, {}
        for node in starts:
            cost = distance(start, point(node))
            costs[node], parents[node] = cost, None
            heapq.heappush(queue, (cost + distance(point(node), goal), cost, node))
        best_end, best_cost = None, math.inf
        while queue:
            estimate, cost, node = heapq.heappop(queue)
            if estimate >= best_cost:
                break
            if cost != costs[node]:
                continue
            if node in ends:
                total = cost + distance(point(node), goal)
                if total < best_cost:
                    best_end, best_cost = node, total
            for dx, dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
                nxt = (node[0] + dx, node[1] + dy)
                if not (0 <= nxt[0] <= nx and 0 <= nxt[1] <= ny):
                    continue
                if not self.segment_clear(point(node), point(nxt)):
                    continue
                next_cost = cost + distance(point(node), point(nxt))
                if next_cost < costs.get(nxt, math.inf):
                    costs[nxt], parents[nxt] = next_cost, node
                    heapq.heappush(queue, (next_cost + distance(point(nxt), goal), next_cost, nxt))
        if best_end is None:
            raise NoRouteError("No connected route at configured grid resolution")
        vertices = []
        while best_end is not None:
            vertices.append(point(best_end))
            best_end = parents[best_end]
        raw = [start] + list(reversed(vertices)) + [goal]
        simplified, index = [start], 0
        while index < len(raw) - 1:
            nxt = len(raw) - 1
            while nxt > index + 1 and not self.segment_clear(raw[index], raw[nxt]):
                nxt -= 1
            if raw[nxt] != simplified[-1]:
                simplified.append(raw[nxt])
            index = nxt
        return tuple(simplified)


@dataclass(frozen=True, slots=True)
class LocalWindEstimate:
    angle_world_rad: float  # world-frame direction wind blows TOWARD
    valid: bool


@dataclass(frozen=True, slots=True)
class PlannerInput:
    position_xy: Point
    heading_rad: float
    current_goal_xy: Point | None
    route: tuple[Point, ...]
    simulation_time: float
    wind: LocalWindEstimate | None = None


@dataclass(frozen=True, slots=True)
class PlannerConfig:
    nominal_distance: float = 500.0
    maximum_distance: float = 550.0
    lateral_angles_rad: tuple[float, ...] = (-0.25, 0.25)
    arrival_radius: float = 30.0
    replan_period: float = 10.0
    minimum_hold_time: float = 30.0
    improvement_threshold: float = 25.0
    smoothing: float = 0.75  # fraction of new direction; applied identically in all modes
    map_distance_weight: float = 1.0
    wind_weight: float = 0.3
    turn_weight: float = 20.0
    change_weight: float = 0.1

    def __post_init__(self):
        numeric = (self.nominal_distance, self.maximum_distance, self.arrival_radius,
                   self.replan_period, self.minimum_hold_time, self.improvement_threshold,
                   self.smoothing, self.map_distance_weight, self.wind_weight,
                   self.turn_weight, self.change_weight, *self.lateral_angles_rad)
        if not all(math.isfinite(v) for v in numeric):
            raise ValueError("Planner parameters must be finite")
        if not (0 < self.nominal_distance <= self.maximum_distance <= 550):
            raise ValueError("Local target range must stay within nominal 500 m envelope")
        if self.nominal_distance < 450 or not 0 <= self.smoothing <= 1:
            raise ValueError("Invalid nominal distance or smoothing")
        if min(self.arrival_radius, self.replan_period, self.minimum_hold_time,
               self.improvement_threshold, self.map_distance_weight, self.wind_weight,
               self.turn_weight, self.change_weight) < 0:
            raise ValueError("Planner thresholds and weights must be nonnegative")


@dataclass(frozen=True, slots=True)
class CandidateScore:
    target_xy: Point
    remaining_map_distance: float
    local_wind_penalty: float
    turn_penalty: float
    change_penalty: float
    total: float


@dataclass(frozen=True, slots=True)
class PlannerDecision:
    target_xy: Point
    candidates: tuple[CandidateScore, ...]
    reason: str
    wind_used: bool


class LocalWaypointPlanner:
    def __init__(self, static_map: StaticMap, config: PlannerConfig | None = None,
                 mode: str = "geometry_only"):
        if mode not in ("geometry_only", "estimated_local", "oracle_local"):
            raise ValueError("Unknown planner mode")
        self.static_map, self.config, self.mode = static_map, config or PlannerConfig(), mode
        self._last_replan = None
        self._last_switch = None
        self._last_time = None
        self._target = None

    def _forward_point(self, position, route):
        if len(route) == 1:
            return route[0]
        # Project onto the nearest route segment, then walk forward 500 m.
        best = None
        for i, (a, b) in enumerate(zip(route, route[1:])):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length2 = dx * dx + dy * dy
            t = 0 if length2 == 0 else max(0., min(1., (
                (position[0] - a[0]) * dx + (position[1] - a[1]) * dy) / length2))
            p = (a[0] + t * dx, a[1] + t * dy)
            key = (distance(position, p), -i)
            if best is None or key < best[0]:
                best = (key, i, p)
        _, index, p = best
        remaining = self.config.nominal_distance
        for b in route[index + 1:]:
            length = distance(p, b)
            if length >= remaining and length > 0:
                return (p[0] + (b[0] - p[0]) * remaining / length,
                        p[1] + (b[1] - p[1]) * remaining / length)
            remaining -= length
            p = b
        return route[-1]

    def plan(self, visible: PlannerInput) -> PlannerDecision:
        if type(visible) is not PlannerInput:
            raise TypeError("Planner requires the explicit PlannerInput whitelist")
        p, final, cfg = visible.position_xy, visible.route[-1] if visible.route else None, self.config
        if final is None:
            raise NoRouteError("Route is empty")
        if not all(math.isfinite(v) for v in (*p, visible.heading_rad, visible.simulation_time)):
            raise ValueError("Visible position, heading and time must be finite")
        if self._last_time is not None and visible.simulation_time < self._last_time:
            raise ValueError("Planner time must be monotonic; create a new instance per episode")
        if any(not self.static_map.segment_clear(a, b) for a, b in zip(visible.route, visible.route[1:])):
            raise NoRouteError("Route segments violate the static map")
        # Establish map reachability separately from the finite local candidate set.
        self.static_map.route(p, final)
        current = visible.current_goal_xy
        current_valid = (current is not None and distance(p, current) <= cfg.maximum_distance
                         and distance(p, current) > cfg.arrival_radius
                         and self.static_map.segment_clear(p, current))
        wind = visible.wind
        use_wind = (self.mode != "geometry_only" and wind is not None and wind.valid
                    and math.isfinite(wind.angle_world_rad))
        targets = [current] if current_valid else []
        if distance(p, final) <= cfg.nominal_distance and self.static_map.segment_clear(p, final):
            targets.append(final)
        forward = self._forward_point(p, visible.route)
        heading = math.atan2(forward[1] - p[1], forward[0] - p[0])
        for offset in (0.0, *cfg.lateral_angles_rad):
            direction = heading + offset
            if current_valid:
                old = math.atan2(current[1] - p[1], current[0] - p[0])
                direction = old + cfg.smoothing * angle_difference(direction, old)
            target = (p[0] + cfg.nominal_distance * math.cos(direction),
                      p[1] + cfg.nominal_distance * math.sin(direction))
            targets.append(target)
        scores = []
        for target in targets:
            if any(distance(target, s.target_xy) < 1e-8 for s in scores):
                continue
            if not self.static_map.segment_clear(p, target):
                continue
            try:
                tail = self.static_map.route(target, final)
            except NoRouteError:
                continue
            local_distance = distance(p, target)
            remaining = local_distance + sum(distance(a, b) for a, b in zip(tail, tail[1:]))
            direction = math.atan2(target[1] - p[1], target[0] - p[0])
            # Upwind motion points against blowing-toward wind: wind + pi.
            wind_cost = (cfg.wind_weight * min(local_distance, cfg.nominal_distance)
                         * max(0., math.cos(direction - wind.angle_world_rad - math.pi)) ** 2
                         if use_wind else 0.)
            turn = cfg.turn_weight * abs(angle_difference(direction, visible.heading_rad))
            change = cfg.change_weight * distance(target, current) if current_valid else 0.
            scores.append(CandidateScore(target, remaining, wind_cost, turn, change,
                                         cfg.map_distance_weight * remaining + wind_cost + turn + change))
        if not scores:
            raise NoLocalTargetError("No safe straight candidate in the bounded 500 m set")
        best = min(scores, key=lambda s: s.total)
        incumbent = next((s for s in scores if current_valid and s.target_xy == current), None)
        externally_changed = current != self._target
        hold_start = visible.simulation_time if externally_changed or self._last_switch is None else self._last_switch
        reason = "selected"
        if incumbent is not None:
            if self._last_replan is not None and visible.simulation_time - self._last_replan < cfg.replan_period:
                best, reason = incumbent, "replan_period"
            elif visible.simulation_time - hold_start < cfg.minimum_hold_time:
                best, reason = incumbent, "minimum_hold"
            elif best.total >= incumbent.total - cfg.improvement_threshold:
                best, reason = incumbent, "hysteresis"
        if self._last_replan is None or visible.simulation_time - self._last_replan >= cfg.replan_period:
            self._last_replan = visible.simulation_time
        if externally_changed or best.target_xy != current:
            self._last_switch = visible.simulation_time
        self._last_time, self._target = visible.simulation_time, best.target_xy
        return PlannerDecision(best.target_xy, tuple(scores), reason, bool(use_wind))
