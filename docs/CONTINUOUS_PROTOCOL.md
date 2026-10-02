# Continuous physics protocol

`src/sailboat_routing/continuous.py` implements `ContinuousPhysics(modules, total_time_limit=2400, world_radius_limit=5000)` using the original real sailboat simulator. Give each instance its own `SeniorModules`; mutable inherited globals are not shared between instances. The immutable source snapshot and `runtime.py` remain unchanged.

## Audited adaptation

Before compiling, the adapter requires the inherited environment file SHA256 to match the Stage A manifest: `8668f769194b65857667b255eeca6467e45d3e248131ea46af245bfbdc156313`. It parses the actual original `step(self, action)` and verifies its exact original truncation branch, empty-info return, integration-failure initialization/four failure assignments and rollback branch. Unrecognized structure raises `UpstreamStepMismatch` rather than guessing from the legacy truncated flag.

Only two AST fields change:

1. The condition `integration_failed or dis_to_yuandian >= 750 or globals.current_time >= globals.total_time` becomes `integration_failed`.
2. The empty return info becomes `{"integration_failed": integration_failed}`.

Before compilation, reversing these two edits must recover an AST identical to the entire original function. ODE equations, adaptive timestep logic, failure rollback, integer-degree floor quantization, sail/rudder targets and rates, wind update and all remaining statements are retained. No inherited class or module is patched; the compiled function is bound only to the wrapper's own environment instance. `physics.adaptation` records actual source path, snapshot/source-step/AST hashes and the exact changes for inclusion in run evidence.

## Continuous semantics

- `reset(seed, wind_degrees)` uses the same original initial-state protocol as `OriginalSegment`, with independent saved Python and NumPy random streams. Construction's implicit upstream reset also runs under an isolated RNG context. The Gym instance retains its own RNG.
- No additional observation or actuator noise is used in Stage B; the original Dryden wind remains. Commands pass unchanged through the original `Action_adapter` using `action_space.high.astype(np.float64)`, matching Stage A's `noise_enabled=False` path. No new clipping, rescaling or actuator convention is introduced.
- `set_goal(goal_xy)` updates only the goal slice of `env.state`, `modules.globals.state` and the wrapper's raw-observation cache. It does not reset physics, wind, Dryden state, time, target sail/rudder angles, RNG or reward milestone flags. Both old and new positions in the next original step's progress calculation use the same new goal.
- `raw`, `env` and `modules` are public. `reset` and `step` return detached raw-14 copies. Returned `terminated` is the original distance-to-goal <= 10 m notification: an intermediate goal does not end the continuous task. The runner chooses the final goal and is responsible for segment timing/route-completion logic.
- Wrapper truncation is the OR of reported integration failure, absolute simulation time >= `total_time_limit`, and world-origin Euclidean radius >= `world_radius_limit`. Both limits must be finite and positive. The inherited reward sees only integration-failure truncation; wrapper task limits do not add the old reward penalty. Non-finite observations/rewards raise rather than concealing a failed transition.
- Step info includes integration failure, physical action, raw observation, simulation time, world radius, separate wrapper-limit flags, both legacy-limit flags, `legacy_limits_enforced=False`, and goal notification. Legacy flags are diagnostics only; `globals.total_time` itself is not modified.
- `continuity_snapshot()` returns a JSON-safe dictionary containing `state` (`env.state[:12]`), `target_sail_angle`, `target_rudder_angle`, `time`, `dryden`, current `wind`, and SHA256 hashes for both saved Python/NumPy state and the Gym RNG state. This is evaluation evidence, not planner input.

## Regression coverage and execution

`tests/test_continuous.py` covers one-step exact parity with no-noise `OriginalSegment`, all physical/wind/RNG invariants during goal changes, a real ODE step at x=800 m and time=1001 s without legacy truncation or reset, wrapper time/radius truncation, continuation after an intermediate-goal notification, and interleaved-instance RNG isolation. It checks the public continuity snapshot is JSON serializable and unchanged by goal switches.

Tests and simulations were deliberately not run by this delegated implementation task. The integration owner runs the suite once together with the Stage B real-controller scenarios. Suggested scoped command from NEW_ROOT: `PYTHONPATH=src .venv/bin/python -B -m unittest discover -s tests -p test_continuous.py -v`.
