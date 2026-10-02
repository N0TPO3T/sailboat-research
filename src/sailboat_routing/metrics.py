"""Offline metrics from actual recorded trajectories, never waypoint counts."""
import math

METHODS = ("geometry_only", "oracle_local", "estimated_local")
EFFICIENCY_FIELDS = ("time_s", "path_length_m", "min_safety_clearance_m",
                     "actuator_variation_rad", "target_changes", "tack_count", "wall_seconds")


def _wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def segment_circle_clearance(p0, p1, obstacles):
    """Minimum signed entity and buffered clearance (metres) for a line segment.

    Returns {'entity_m': ..., 'safety_m': ...}; positive means clear, zero
    tangent, negative penetration. Empty obstacles give +inf for both. This
    sampled-trajectory chord approximation cannot prove exact curve safety.
    Obstacles use planner.CircleObstacle's center_xy/entity_radius/safety_buffer.
    """
    if not all(math.isfinite(v) for v in (*p0, *p1)):
        raise ValueError("Segment endpoints must be finite")
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length2 = dx * dx + dy * dy
    entity, safety = math.inf, math.inf
    for obstacle in obstacles:
        cx, cy = obstacle.center_xy
        fraction = 0.0 if length2 == 0 else max(0.0, min(1.0, (
            (cx - p0[0]) * dx + (cy - p0[1]) * dy) / length2))
        distance = math.hypot(p0[0] + fraction * dx - cx, p0[1] + fraction * dy - cy)
        entity = min(entity, distance - obstacle.entity_radius)
        safety = min(safety, distance - obstacle.entity_radius - obstacle.safety_buffer)
    return {"entity_m": entity, "safety_m": safety}


def posthoc_tack_events(times, headings, wind_directions, *,
                        hysteresis_rad=math.radians(10),
                        min_heading_change_rad=math.radians(20)):
    """Detect resolved crossings of upwind, with explicit wind-driven events.

    All angles are world radians; wind blows TOWARD, so upwind = wind + pi.
    Circular per-sample increments are accumulated until the opposite relative
    side exits a +/- hysteresis band. Only paths crossing upwind, not downwind,
    qualify. A tack requires signed boat heading motion toward the crossing of
    at least min_heading_change_rad, with boat contribution >= opposing wind
    contribution. Otherwise the event is wind_driven (not a tack). This is a
    reproducible attribution heuristic, not a causal manoeuvre label. Adjacent
    heading/wind changes must each be < pi to avoid circular sampling aliasing.
    """
    times, headings, wind_directions = list(times), list(headings), list(wind_directions)
    if not len(times) == len(headings) == len(wind_directions):
        raise ValueError("Trajectory arrays must have equal lengths")
    if not (0 < hysteresis_rad < math.pi / 2 and 0 < min_heading_change_rad < math.pi):
        raise ValueError("Invalid angular thresholds")
    if not all(math.isfinite(v) for series in (times, headings, wind_directions) for v in series):
        raise ValueError("Trajectory samples must be finite")
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Trajectory times must strictly increase")
    events = []
    side = 0
    start = None
    boat_motion = wind_motion = 0.0
    crossed = False
    previous_relative = None
    for i, (heading, wind) in enumerate(zip(headings, wind_directions)):
        relative = _wrap(heading - wind - math.pi)
        stable_side = 1 if relative >= hysteresis_rad else -1 if relative <= -hysteresis_rad else 0
        if i and start is not None:
            dh = _wrap(heading - headings[i - 1])
            dw = _wrap(wind - wind_directions[i - 1])
            boat_motion += dh
            wind_motion += dw
            # Unwrapped step crosses 0 (+/- multiples of 2pi), not +/- pi.
            end = previous_relative + dh - dw
            lower, upper = sorted((previous_relative, end))
            crossed |= math.ceil(lower / (2 * math.pi)) <= math.floor(upper / (2 * math.pi))
        if stable_side:
            if side and stable_side != side and crossed:
                direction = -side
                boat_contribution = direction * boat_motion
                wind_contribution = -direction * wind_motion
                kind = ("tack" if boat_contribution >= min_heading_change_rad
                        and boat_contribution >= max(0.0, wind_contribution) else "wind_driven")
                events.append({"kind": kind, "start_index": start, "end_index": i,
                               "start_time_s": times[start], "end_time_s": times[i],
                               "from_side": side, "to_side": stable_side,
                               "heading_change_rad": boat_motion,
                               "wind_change_rad": wind_motion})
            # A stable sample anchors the next excursion; jitter in deadband
            # does not re-anchor or produce repeated side-change counts.
            side, start = stable_side, i
            boat_motion = wind_motion = 0.0
            crossed = False
        previous_relative = relative
    return {"tack_count": sum(e["kind"] == "tack" for e in events),
            "wind_side_change_count": sum(e["kind"] == "wind_driven" for e in events),
            "events": events}


def summarize_paired(rows):
    """Strict three-method scene pairing; efficiency only on common successes.

    Missing or duplicated scene/method rows fail rather than silently shrink the
    denominator. All failed scenes remain in success rates. Failed-row metrics
    may be None; common-success metrics must be finite (clearance may be +inf
    for an obstacle-free scene). Empty/common-all-failure efficiencies are None.
    """
    scenes = {}
    for row in rows:
        scene_id, method = row["scene_id"], row["method"]
        if method not in METHODS:
            raise ValueError(f"Unknown method: {method}")
        if not isinstance(row["success"], bool):
            raise ValueError("success must be a bool")
        scene = scenes.setdefault(scene_id, {})
        if method in scene:
            raise ValueError(f"Duplicate scene/method: {scene_id}/{method}")
        scene[method] = row
    for scene_id, scene in scenes.items():
        if set(scene) != set(METHODS):
            raise ValueError(f"Incomplete paired scene: {scene_id}")
    common = [scene_id for scene_id, scene in scenes.items()
              if all(scene[m]["success"] for m in METHODS)]
    result = {"scene_count": len(scenes), "common_success_count": len(common),
              "common_success_scene_ids": common, "methods": {}}
    for method in METHODS:
        successful = sum(scene[method]["success"] for scene in scenes.values())
        efficiency = None
        if common:
            efficiency = {}
            for field in EFFICIENCY_FIELDS:
                values = [scenes[scene_id][method][field] for scene_id in common]
                if any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or math.isnan(value) or (not math.isfinite(value) and not (
                           field == "min_safety_clearance_m" and value == math.inf)) for value in values):
                    raise ValueError(f"Invalid common-success metric: {method}/{field}")
                efficiency[field] = sum(values) / len(values)
        result["methods"][method] = {"success_count": successful,
                                     "success_rate": successful / len(scenes) if scenes else None,
                                     "efficiency_sample_count": len(common),
                                     "efficiency_mean": efficiency}
    return result
