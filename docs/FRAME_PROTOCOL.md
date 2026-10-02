# Fixed target frame and recurrent memory

`LocalFrame.for_leg(start_xy, goal_xy)` fixes the angle to `atan2(goal-start)` and the origin to `goal - 500 * [cos(angle), sin(angle)]`. It is a rigid transform in physical metres, not a distance rescaling. A leg of length 1000 m therefore starts at local x = -500 m, not at zero. Identical start and goal positions do not define a leg and are rejected.

The frozen 14-dimensional Actor input is encoded as follows:

- World x/y are translated and rotated into the fixed frame.
- Heading (index 3) subtracts the frame angle and wraps in radians.
- Roll, body u/v/p/r, sail and rudder (indices 2 and 4–9) are unchanged.
- Target indices 12/13 are always exactly float32 `[500, 0]`, including after a target switch. The matching frozen zero-variance target statistics are never updated.
- Index 10 is previous distance minus current distance to the **same new target**.
- Index 11 is previous absolute local x-distance minus current absolute local x-distance to that target. Both states use the **same new frame**.
- Without a previous observation, both progress fields are zero. Existing raw progress and target fields are ignored.

Wind conversion subtracts/adds the frame angle and wraps in radians; it preserves whether the caller uses a blowing-to or coming-from direction. No wind information is passed to `encode` or the Actor.

## Target-switch replay

Call `reencode_controller(controller, frame, raw_history, commands)` immediately before a decision. At decision t, `raw_history` is the full causal sequence `s0, ..., st`, including the current undecided observation. `commands` is `a0, ..., a(t-1)`: the normalized commands actually issued by the Actor before actuator noise, clipping or conversion to physical units. Preserve the observations actually visible to the controller (including sensor noise, if enabled); do not replace them with noiseless simulator states.

Every observation is reencoded under the new frame/target; every progress value is recomputed with its preceding observation. The Actor hidden state is reset and exactly t original single-step forwards are replayed:

1. Decision 0 uses current `s0` and recurrent pseudo-history `(s0, zero_action)`.
2. Decision i > 0 uses current `si` and recurrent history `(s(i-1), a(i-1))`.
3. Recomputed actions are discarded. Only actual past commands feed recurrent history.

The current decision t is **not** replayed. On return, `previous` is reencoded `s(t-1)` (or `s0` initially), `previous_action` is actual `a(t-1)` (or zero initially), and `steps` is t. Call `controller.act(returned_observation)` exactly once for the new decision. With t = 0, hidden state remains unadvanced until this call. The inherited `bptt_len=10` training setting is not an online memory window; replay uses the complete history.

Replay temporarily disables the controller feature-capture flag, preserving both its original flag and cached feature, so historical forwards do not enter a live bypass collector. Readout code must use only the subsequent real decision's returned features, not a feature cached before the switch. Actor parameters, evaluation mode and normalizer statistics remain unchanged. The returned elapsed wall seconds include validation, encoding and replay.

Acceptance tests are in `tests/test_frames.py` and use the copied real Actor and normalizer checkpoints, not mock networks. They cover rigid inverses/no scaling, unchanged body fields, wrapped heading/wind, switched-target progress, zero-variance target normalization, every replay prefix beyond 10 steps, h/c and next-action equality, actual-command replay under a changed frame, disabled feature capture and frozen parameters/statistics. Tests are intentionally left for the integration owner to run with `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_frames.py` from NEW_ROOT.
