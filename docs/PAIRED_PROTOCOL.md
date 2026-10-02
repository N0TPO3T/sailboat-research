# Paired local-wind diagnostic protocol

## Scope and isolation

The three methods are `geometry_only`, `oracle_local`, and `estimated_local`.
They share the static map, candidate generation, replanning period, target hold
and switch rules, initial physical state, frozen low-level controller and
readout. Only local wind information changes. `oracle_local` is a diagnostic
current-position/current-time direction reference, not a forecast or global
optimal upper bound. The estimated method falls back to the same geometry
policy when its causal estimate is invalid, never to true wind.

`wind_fields.SyntheticWindField(seed, base_direction_rad, profile='stable',
horizon=2400, base_speed=8.0)` is an environment-private field, with no environment
binding, external weather data, planner-grid dependency or full-field
reconstruction. `sample((x_m, y_m), physical_time_s)` returns `(speed_m_s,
blowing_toward_world_angle_rad)`; angles lie in `[-pi, pi)`. Queries must be
finite and time must lie in `[0, horizon]`. At noninteger times, the precomputed
integer-second perturbation is linearly interpolated; analytic spatial and
temporal waves are evaluated at the actual time. Speed is always positive.

A private Python RNG is used only at construction. It generates phases and
independent coarse perturbation knots. Smoothstep interpolation makes knot
changes gradual before integer-time precomputation. Queries do not consume RNG
state; Python's global RNG and NumPy's global RNG are untouched. The same seed,
parameters, physical position and time give the same answer regardless of query
order/count, candidate enumeration or method trajectory. Different trajectories
sample different parts of the SAME field, not a forced identical wind sequence.
Observation-noise randomness must remain a separate runner-owned stream indexed
by physical time; this class does not bind or implement observation noise.

Public frozen `WindProfile` parameters in `PROFILES` are:

| profile | direction wave amplitude | speed fraction | time period (s) | spatial wavelength (m) | perturbation knot period (s) | perturbation amplitude |
|---|---:|---:|---:|---:|---:|---:|
| stable | 0 deg | 0 | 1200 | 2000 | 120 | 0 deg |
| slow | 25 deg | 0.12 | 1800 | 2400 | 180 | 3 deg |
| fast | 45 deg | 0.20 | 480 | 1200 | 60 | 6 deg |

The direction wave is a 0.65/0.35 mixture of two oblique sine waves, the second
at 0.53 of the temporal frequency. The speed sine has temporal factor 0.73.
These are bounded synthetic development conditions, not calibrated weather.
Stable wind is exactly fixed everywhere and at every valid time. `diagnostics()`
returns profile parameters, seed, horizon, and fixed/spatial/temporal flags for
ENVIRONMENT/OFFLINE metadata only. Neither field, seed, query function, metadata,
future/remote truth nor full environment/info objects belong in formal planner
inputs. Truth may enter dynamics, offline labels and logs. An oracle wrapper may
expose only true direction at the current boat location/time, without speed or
arbitrary query access. The field API does not enforce this capability boundary
by itself; runner/planner isolation must enforce it.


Varying profiles expose environment/offline-only `change_onsets`, a tuple of
integer physical seconds. Stable is empty. Slow/fast use
`(int(min(100, horizon / 4)),)`, normally `(100,)`. Before and at the onset,
the whole field equals base wind. After onset, a smoothstep amplitude envelope
activates the actual space/time waves and perturbation over 60 seconds (slow)
or 30 seconds (fast), shortened to the remaining horizon for very short fields.
Thus the marker identifies a real, continuous onset, not a fictitious label.
It is not a future-wind signal permitted to the planner. The runner may apply
1 Hz zero-order hold: sample at `(x_t,t)` before the action, then replace the
legacy wind update with `sample(x_{t+1},t+1)` for the next action. Arbitrary
extra offline queries leave that action-step wind unchanged.

## Actual-trajectory metric contracts

These helpers do not inspect observation dimensions, Actor internals or planner
waypoint counts. The runner supplies already-recorded physical trajectory data.

`segment_circle_clearance(p0, p1, obstacles)` accepts world-metre endpoints and
existing `planner.CircleObstacle` objects (`center_xy`, `entity_radius`,
`safety_buffer`). It returns `{'entity_m': float, 'safety_m': float}`: the minimum
signed line-segment distance minus entity radius, and minus entity radius plus
safety buffer, respectively. Positive is clear, zero tangent, negative overlap.
No obstacles yields positive infinity for each. Evaluate every adjacent actual
trajectory segment and take separate minima; a one-sample trajectory can use a
degenerate segment. Safety-buffer overlap is not necessarily entity collision.
**Sampled trajectory chords approximate the true motion curve and cannot prove
exact continuous-curve safety between samples.** Report the sampling interval.
For strict JSON, serialize obstacle-free positive infinity as null together with
an explicit no-obstacles flag; retain infinity in in-memory summary inputs.

`posthoc_tack_events(times, headings, wind_directions, hysteresis_rad=10 deg,
min_heading_change_rad=20 deg)` consumes aligned, finite arrays with strictly
increasing physical times, world boat headings and world blowing-TOWARD winds.
Upwind is `wind + pi`. It uses circular increments and relative-side hysteresis,
requiring an actual crossing of upwind, not a downwind gybe. An excursion becomes
resolved when the opposite side exits the deadband. A tack additionally needs
at least the minimum signed boat-heading change in the crossing direction and
boat contribution at least as large as the wind's crossing contribution.
Otherwise the resolved upwind side change is `wind_driven` and excluded from
`tack_count`. The result contains `tack_count`, `wind_side_change_count`, and
`events`; each event includes kind, sample indices/times, from/to side and
signed accumulated heading/wind changes. This mixed-motion attribution is an
explicit heuristic, not causal proof. Adjacent heading and wind changes must
each be less than pi; sparse samples can alias or miss excursions. Counts never
substitute target/waypoint changes for boat manoeuvres.

## Paired row and summary schema

A runner row uses these fields; all are available from the actual private
environment, trajectory, target log or host clock (no additional sensor or
unavailable model label is required):

| field | meaning |
|---|---|
| `scene_id` | shared scene identifier, including failed scenes |
| `method` | exactly one of the three method names |
| `success` | Python bool, full-task outcome |
| `time_s` | elapsed physical task time, not host time |
| `path_length_m` | sum of actual adjacent world-position chord lengths |
| `min_safety_clearance_m` | minimum buffered actual-trajectory segment clearance |
| `actuator_variation_rad` | sum of absolute per-step changes of actual sail and rudder angles, not proposed normalized actions |
| `target_changes` | count of applied local-target replacements, distinct from tacks |
| `tack_count` | posthoc boat manoeuvre count from the detector above |
| `wall_seconds` | measured host elapsed method/episode time, with measurement scope recorded |

Optional offline row/log fields include failure reason, entity clearance,
wind-driven event count, event list, sampling interval and field diagnostics.
Log failed-run observed metrics when available; unavailable values may be null.
`summarize_paired(rows)` needs finite numeric metrics for common-success rows
(except positive infinite clearance on maps without obstacles). Failed rows need
only identifier/method/success for aggregation. Counts should be integers.

Exactly one row per scene/method is required. Missing pairs, duplicate pairs and
unknown methods raise rather than quietly changing denominators. Success rates
use ALL paired scenes, including complete failures. Efficiency means for all
seven numeric fields use only scenes where ALL THREE methods succeeded, with
identical denominators. The result includes `scene_count`,
`common_success_count`, `common_success_scene_ids` and per-method
`success_count`, `success_rate`, `efficiency_sample_count`, `efficiency_mean`.
With zero common successes, `efficiency_mean` is None (JSON null), never an
invented zero or an average of method-specific survivors. With no scenes,
success rate is also None. Preserve failed raw rows and reasons; do not tune or
filter until a method wins. These are development diagnostics, not significance
claims or evidence that a planner necessarily improves performance.

## Verification ownership

`tests/test_wind_fields_metrics.py` covers query-order/count/trajectory identity,
global random-state isolation, fractional-time continuity, angular wrap, entity
versus buffer clearance, actual boat versus wind-driven crossings, downwind and
hysteresis rejection, common-success denominators, complete failures, empty
inputs and malformed pairings. This assignment adds code/tests only and runs no
tests, simulations or experiments. Central validation and the C/D real runner
are owned by the integrating agent; no performance result is claimed here.
