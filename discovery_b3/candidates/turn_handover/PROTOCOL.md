# Frozen pilot protocol — 2026-10-09

C1 turn handover, one local CPU process, no GPU. No claim of industry-standard accuracy or real-hardware validation. This is a screening test of a mature reference governor against competent simple control.

## Before held-out geometry run

Admission receipt fixes the upstream six-DOF Otter model. Development `runs/dev_v1` contains three rate-cap trials on R=10 m, cruise=1.5 m/s, no current. All finish safely. Rate caps 0.08/0.12/0.18 rad/s give 156/160/158 m effective measurement bins and 146.0/132.5/127.3 s. Choose 0.12 rad/s to prioritize full effective measurement length, retaining the faster 0.18 trial as evidence. This is development calibration, not independent confirmation. Feedback gains are fixed for all methods; no further gains are tuned on the eight geometries below.

Common speed PI and yaw PID/feedforward, actual-actuator residual anti-windup, asymmetric force inversion, exact yaw-priority allocation, 4m LOS lookahead, 0.15m/s2 reference acceleration/braking bound. Course is computed from observed body ground velocity rotated by observed heading; simulator current parameter is not passed to controllers. No future wind/current query. Known geometric path curvature is allowed.

## Eight fixed tasks and methods

Full Cartesian product: radius {8,16} m × cruise {1.2,1.8} m/s × fixed eastward current {0,0.3} m/s. Each task has 80m first line, feasible semicircle, 80m returning line. Beginning at first-line origin with initial forward speed cruise; motor speed initialized from nominal no-current drag. 500 s timeout. Straight lines along x, spacing 2R.

Permissible region is x∈[−4,80+R+4], y∈[−4,2R+4] m for every method. Full 2×1.08m rectangular hull must remain in it, with orientation integrated. This 2L margin is an engineering scenario, not a shore derived from a survey chart. Violations retained; do not retune boundary after seeing results.

Three methods: curvature pre-braking baseline; same baseline with speed reduced by max(0.35,cos(min(|heading error|,π/2))²); same baseline with reference speed additionally bounded by available total thrust after reserving requested yaw moment, divided by nominal forward drag coefficient. The governor uses present requested yaw only, not future simulation. All share yaw-priority physical allocation, so governor may be redundant; no new module is required to win.

## Unit and metrics

One completed turn-handover task is a sample. Deterministic paired scenarios, not eight random-seed population estimates. dt=0.05s; repeat one fixed representative hard case at 0.025s for all methods after main.

Effective line length: count distinct 1m bins on either straight line where center cross-track ≤1m, observed ground course within10°, ground speed within [0.8,1.2]×cruise. Total maximum160m, same conditions for every method. A bin records at least one valid observation, not guaranteed continuously valid whole1m; this screening approximation is explicitly retained. Return recovery: first continuous3s meeting these conditions after arc exit; report both absolute time and delay after arc exit. Also report full task time, completion, minimum hull boundary clearance, force activity ∫Σ|f_i|dt, shaft-rate variation and propeller reversals. Force activity is not electrical energy.

Continuation gate fixed before eight-task run: candidate must rescue ≥2 task failures without causing new failures, OR add ≥8m effective line length in ≥2 tasks without new failures and with mean duration penalty ≤10%; normal R16/current0 cases must lose no more than2m and incur no more than5% time penalty. These are engineering screening gates, not statistical claims or published survey standards. Candidate need not defeat every method, but the best mature simple solution defines the real remaining gap. If strong simple control suffices, report that application result without inventing novelty. If all three are close, stop this candidate rather than make arbitrarily narrow boundaries or add favorable seeds.

## Verification

Hash code/config and store full trajectories per method. Check finite states, paired case identity, force bounds, monotone time/progress, same upstream dynamics; cross-check endpoint and actual hull clearance from raw trajectories. Preserve failed and development runs. Common implementation errors require fair rerun, not credit to governor. Partial-thrust loss is not part of this pilot and cannot be silently added as selected favorable cases.

## Common baseline correction before v2

The v1 batch completed, but ground-current cases showed sustained straight-line sampling loss. Review of implemented information flow found heading LOS omitted ordinary sideslip compensation although measured body ground velocity was already available to every method. This is an incomplete simple baseline, not evidence for a new method. v2 uses common ground-course LOS: desired heading = desired geometric course − atan2(measured body lateral velocity, measured body forward velocity). All three methods receive exactly this common correction, with no hidden current query. Same eight tasks, parameters, metrics and gate; v1 preserved as diagnostic only. Rerun development then frozen tasks. No success claim from correcting this omission.

## Shared stabilization repair before v3 (all eight cases are now development-seen)

v2 failed timestep sensitivity: halving dt changed the difficult-case effective line count by18–31m. Its direct instantaneous drift-angle feedback and low heading stiffness produced oscillatory straight-line course. Its differenced discrete LOS lookahead also generated clipped derivative pulses. Therefore v2 is not acceptable final comparison evidence.

Common repair: replace discrete LOS derivative feedforward by geometric curvature feedforward; low-pass the measured sideslip angle (5s); use 0.025s timestep. A six-point local test of lookahead4/8/12m and damping45/90 with kp30 remained poor. A second six-point development test on R10,1.8m/s,current0.3 evaluated lookahead4/8 and kp30/100/200 at damping90. Fixed kp200, kd90, lookahead4 for largest effective line length157/160m (development), keeping all runs. This is feedback calibration shared by all methods, not candidate-specific advantage. No geometry boundary or sampling tolerance changed.

Development dt0.025→0.0125 gives157→156m,113.375→113.350s, minimum margin3.0447→3.0224m. Acceptable for an engineering screening (1m bin granularity); selected-task numerical check repeated on final comparison. FROZEN_CONFIG_v1 preserves original parameters, FROZEN_CONFIG is shared repaired configuration. Same fixed eight-task set rerun as exploratory paired screening, not unseen confirmation. Original continue gate remains unchanged.
