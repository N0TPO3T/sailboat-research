# Static-map local waypoint planner

## Status and gate

This is an independently implemented geometric module, not evidence of closed-loop performance. Stage B's predeclared 6/6 gate failed (5/6 real approximately 1 km scenarios; headwind seed 11 timed out on the first segment). Consequently **the geometry_only / oracle_local / estimated_local paired closed-loop experiments have not been run**, and no wind readout has been fitted for these comparisons. The frozen Actor and 14-dimensional low-level protocol are unchanged. Unit cases and the standalone API do not substitute for the failed B gate. This module adds no simulator runner, collector, training, or performance report.

## Map and routes

`StaticMap.bounds = (xmin, xmax, ymin, ymax)` uses world meters and inclusive rectangular bounds. Obstacles are circles with separate `entity_radius` and `safety_buffer`; geometry excludes their sum, including tangency. The buffer is a map clearance choice, **not a guarantee for the actual controller trajectory**. Grid edges, simplified route segments, and candidate boat-to-target lines are collision checked. Boundaries themselves have no additional implicit buffer.

`StaticMap.route(start, final)` first checks a direct line, otherwise uses deterministic eight-connected A* at the configured grid resolution. Endpoint connections are to nearby visible grid nodes; grid corners cannot cut through a circle. A greedy line-of-sight pass removes unnecessary grid vertices. A coarse grid may fail in a real narrow passage: `NoRouteError` means no route at this discretization, not a mathematical proof of continuous-space impossibility. Start/goal outside the map or on an inflated obstacle also fail explicitly.

Returned route vertices encode **critical geometric turns**, not mandatory low-level waypoints. Relay targets are chosen separately. A* grid nodes are never automatically dispatched to the Actor. The planner projects the boat onto the nearest route segment, walks forward approximately 500 m along the route, and uses that bearing to generate a small local candidate set.

## Visible information and modes

The only per-decision input is frozen, slotted `PlannerInput`:

- `position_xy`: world position in meters;
- `heading_rad`: world heading, radians;
- `current_goal_xy`: already assigned local target, or `None`;
- `route`: static geometric route ending at the final goal;
- `simulation_time`: monotonic current simulation time in seconds;
- optional `wind = LocalWindEstimate(angle_world_rad, valid)`.

There is no environment, complete info dictionary, speed, field state, seed, wind query, arbitrary callback, future observation, or remote forecast input. The module holds only the static map, common parameters, mode and its own timing/target state. It imports no simulator or random generator.

`geometry_only` ignores the wind field even if provided. `estimated_local` uses only a valid finite local angle; absent/invalid/nonfinite wind falls back to exactly the same geometric policy, without consulting truth. `oracle_local` consumes the same minimal local angle record: the caller is responsible for obtaining **one current boat-position/current-time angle** using the separate diagnostic oracle interface. The planner cannot query a wind field. Estimated and oracle modes differ in their caller's angle source, not planner parameters or code. Readout outputs can be converted explicitly using `LocalWindEstimate(readout.world_rad, readout.valid)`.

Wind is the world direction it blows **toward**, in radians. Upwind travel has bearing `wind.angle_world_rad + pi`; a coming-from source must be converted by adding pi first. No angle is copied to unvisited map positions.

## Candidates, score and switching

New nonfinal candidates are exactly the configured nominal distance (default 500 m): forward and two angular offsets (default ±0.25 rad). A final goal within nominal distance is additionally eligible if its line is clear. A retained goal may become shorter as the boat approaches it; it remains eligible until within `arrival_radius`, provided it is clear and at most `maximum_distance` away. The 550 m retained-goal cap is a guard near the nominal scale, **not a claim that 550 m was separately validated in B**. This code never dispatches a remote 3 km/5 km endpoint directly. Tight turns may leave no collision-free nominal-distance candidate; `NoLocalTargetError` reports this limitation rather than silently shortening the target or pretending the controller can follow a grid corner. Initial routes and the small candidate heuristic therefore do not guarantee planner completeness.

With an incumbent goal, target-bearing smoothing interpolates the wrapped angle using the common `smoothing` fraction. It is independent of wind validity and source. Smoothed candidates are placed back on the nominal-distance circle and checked against the map again. The incumbent itself is preserved unchanged, not smoothed away.

Each candidate reports unweighted `remaining_map_distance` and already weighted wind, turn and change penalties, plus total:

- map distance = boat-to-candidate distance + simplified A* map distance candidate-to-final;
- wind = `wind_weight * min(local_distance, nominal_distance) * max(0, cos(bearing - wind - pi))^2`;
- turn = `turn_weight * abs(wrapped(bearing - heading_rad))`;
- change = `change_weight * distance(candidate, current_goal)` for a valid incumbent;
- total = `map_distance_weight * map_distance + wind + turn + change`.

Units/scales are heuristic cost meters: map weight is dimensionless; wind weight dimensionless, turn weight meters/radian, change weight dimensionless. The wind term is **only a short local soft penalty**. Upwind targets remain candidates; the Actor can still tack. This is neither a globally wind-optimal route nor an accurate sailing-time prediction. Candidate map-distance estimates assume straight candidate travel solely for geometry and scoring, not actual vessel motion.

The valid incumbent is retained until both the replan period and minimum hold time allow a switch, and the best score improves by more than `improvement_threshold`. An externally changed incumbent starts a new hold interval. An arrived or geometrically invalid incumbent bypasses hold for a replacement. The caller must feed the returned target as the next `current_goal_xy`; construct a new planner per episode. Instances do not share timing or goal state. Scores are returned even on hold decisions for diagnostics; no method makes random draws or alters physics RNG streams. Unreachable maps and empty candidate sets are explicit errors, not artificial success fallbacks.

## Simple API and scoped verification

Run only on the server, from `/home/ot/Students/hs/sailboat-routing-v0` with the project's environment:

```python
import json
from sailboat_routing.planner import (
    CircleObstacle, StaticMap, PlannerConfig, PlannerInput, LocalWaypointPlanner,
)

chart = StaticMap((0, 1200, -400, 400),
                  (CircleObstacle((600, 0), 100, 40),), grid_resolution=25)
route = chart.route((0, 0), (1200, 0))
# For an unobstructed API smoke, use a straight route/map:
chart = StaticMap((-1000, 6000, -1500, 1500))
route = chart.route((0, 0), (1000, 0))
with open("configs/planner.json") as handle:
    config = PlannerConfig(**json.load(handle))
planner = LocalWaypointPlanner(chart, config, mode="geometry_only")
decision = planner.plan(PlannerInput((0, 0), 0.0, None, route, 0.0))
assert decision.target_xy == (500.0, 0.0)
print(decision)
```

`tests/test_planner.py` covers map detours and buffered gaps; map bounds/no-route errors; bounded-candidate infeasibility; invalid/absent estimate fallback; information whitelist and hidden-state noninterference; blowing-toward convention and soft upwind cost; matching oracle/estimated behavior for the same angle; retained goals, hold, replan period and hysteresis; distant and nearby endpoints; independent instances and Python/NumPy RNG preservation. Test and smoke execution is owned by the integration agent; this module's author did not run tests or experiments during concurrent implementation.

Scoped unit command for integration: `.venv/bin/python -m unittest discover -s tests -p test_planner.py -v` (set `PYTHONPATH=src` if the package is not installed). No closed-loop comparison is authorized by this command.
