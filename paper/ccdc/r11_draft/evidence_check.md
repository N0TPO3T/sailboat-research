# R11 independent evidence check

Checked 2026-10-05 from existing artifacts only. No new episodes, learning, parameter search, or scientific source changes. All paths below are relative to `/home/ot/Students/hs/sailboat-routing-v0`. This is a writing aid, not an external scientific certification.

## Verified numbers and source identity

Read R10 decision/report, METHOD_SCOPE, R8 note/report and actual source. Current `r8_model.py`, `r8_planner.py`, `r7_dynamic.py`, `frames.py`, `obstacle_candidate.py`, `r6_controller.py`, `continuous.py`, and `scripts/run_r8.py` match `runs/r10_decision_20261005/SOURCE_HASHES.json` SHA256 entries. Therefore the line references below describe the frozen implementation.

Independent aggregation from each batch's `rows.json`:

| Batch | Safe completion (sampled / reactive / hold60 / nominal_hold) | sampled minus reactive, common safe | Entire trajectory equal, sampled/reactive |
|---|---|---|---|
| R8 confirmation | 30/30, 28/30, 30/30, not run | n=28, mean +15.285714 s, max +267 s | 22/30 |
| R8 long | 4/4, 3/4, 4/4, not run | n=3, mean +8.666667 s, max +26 s | 2/4 |
| R10 confirmation | 12/12, 12/12, 12/12, 11/12 | n=12, mean +27.083333 s, max +271 s | 10/12 |

The trajectory equality check compared complete parsed `trajectory` lists, including state, command, target, observation and recorded clearance fields, not just time or XY endpoints. In R10 only `r10new_mixed_pressure_0` and `r10new_endpoint_0` differ; all other ten match. R8 long matching cases are the two overtaking cases. No pooled success statistic should combine these batches.

Raw roots: `runs/r8_closedloop_20261005T062543Z/{confirmation,long}` and `runs/r10_decision_20261005/confirmation`. Individual raw traces are `<scene_id>__<variant>/trace.json`; complete row fields are also in each trace. Independently recomputed synchronous segment distances and safe-completion classification for all 150 traces (90+12+48). Dynamic margins matched within 3e-14 m; static margins checked within 1e-3 m (float32 subtraction in original static metric versus independent double-precision arithmetic). Absent obstacles serialize infinite margin as null and were treated as +infinity, not zero. All safe-completion labels agree.

Recomputed every one of the 12 entries in R10 `comparisons.json` from `analysis_rows.json`: paired set sizes, wins/losses, common-safe denominators, mean differences and maxima agree. The 13 seen dynamic cases give sampled13, reactive11, nominal_hold9, hold60 13 safe completions. For new R10 data, sampled minus nominal_hold is -7.090909 s over 11 common-safe pairs; sampled minus hold60 is -9.25 s over 12. CPU sums are sampled777.047455 s, reactive130.833237 s, hold60328.768829 s, nominal_hold693.426115 s. R8 confirmation sampled CPU2640.783111 s, reactive403.881863 s, hold601047.181906 s. CPU sum is not wall time or deadline guarantee.

## Low-level interface: exact 18 inputs

`frames.py:35-77`, `r6_controller.py:67-85`, `r7_dynamic.py:47-59` define current interface. With reference g, frame angle theta is bearing from the boat at reference application to g. Frame origin is g-500[cos(theta),sin(theta)], so g has local coordinates (500,0). This is rigid translation/rotation, not length scaling.

| Zero-based indices | Meaning and unit |
|---|---|
| 0,1 | local-frame boat x,y, m |
| 2,3 | roll phi; wrapped heading psi-theta, rad |
| 4,5 | body-frame surge/sway u,v, m/s (not rotated again) |
| 6,7 | roll/yaw rates p,r, rad/s |
| 8,9 | actual sail/rudder angles, rad, not accumulated commanded setpoints |
| 10 | previous-minus-current Euclidean distance to the reference, m |
| 11 | previous-minus-current absolute local x displacement from x=500, m |
| 12,13 | reference coordinates 500,0, m |
| 14,15 | nearest selected obstacle encoded distance and heading-relative bearing, m/rad |
| 16,17 | second selected obstacle pair, m/rad |

Initial progress features are zero. Static and currently observed valid moving obstacles form one set. Encoded distance is max(0, center distance - exclusion radius +40 m). Select encoded distances <=150 m; sort Python (distance,bearing) tuples, retain two, pad missing pairs with (0,0). Bearing is wrapped world bearing minus world boat heading. This adapted input is NOT the inherited V3 120-degree FOV/persistent detection implementation. Historical dynamic pairs are reconstructed using each historical observation, not current obstacle positions retroactively.

`obstacle_candidate.py:70-131`: frozen `Actor(18,2,(256,256))`, frozen z-score `(x-mean)/(sqrt(var)+1e-6)`, eval mode, deterministic tanh output. Previous state and previous normalized command feed persistent recurrent memory; a ten-slot attention-output history is not a ten-step recurrent-state reset. `frames.py:80-124` resets and rebuilds memory when the reference frame changes: it reencodes observed s0..st and replays exactly t forwards, inserting actual commands a0..a(t-1), leaving decision t for caller. It never substitutes predicted commands for actual past commands. No online optimizer or normalization update is used.

## Actuation and physical timing

`continuous.py:161-170`, `third_party/senior/sailboat_s14.py:165-167,197,216-253`: normalized two-vector action in [-1,1] is multiplied by pi/18 radians. Each physical increment is floor-divided by one degree (signed floor, not rounding or truncation toward zero), then accumulated into setpoints clipped to +/-pi/2 sail and +/-pi/6 rudder. Actual angles move toward those setpoints with rate limit pi/18 rad/s each. The one-second transition uses inherited adaptive Dormand-Prince integration, with linear actuator angle interpolation during the step. Actual R8 dynamics come from `third_party/senior/sailboat_s14.py`, not the separately archived V3 obstacle environment. The 18D asset supplies policy/normalization only. No additional actuator/sensor noise; dropout is disabled.

`run_r8.py:37-76`: at t compute action a_t under the current reference, then select a new reference; advance true physics from t to t+1 using already computed a_t; apply a queued changed reference after that step. Default extra goal_delay=0 means selection t, application t+1, earliest changed physical transition t+1 to t+2. The trace row at t+1 records the old target because it is appended before reference application; use `changes` for exact applied times. Physics is paused during planning, so CPU/wall measurements do not establish online 15-second deliverability.

## Causal wind fit and rollout initialization

`r8_model.py:16-47`: wind starts at world vector (0,8) m/s. With history s0..st, t>=6, the fit uses transitions (t-6,t-5), (t-4,t-3), (t-2,t-1); it does not use (t-1,t). For shorter history use all consecutive pairs and take every other pair, and return the prior without fitting if fewer than three pairs exist. This startup branch is normally bypassed because first allowed prediction is t>=10.

For each chosen pair compute arithmetic midpoint state, replacing heading midpoint with wrapped shortest-angle midpoint. Target acceleration is the difference of raw components [u,v,p,r] across the one-second pair. Evaluate the inherited derivative at midpoint state and midpoint actual sail/rudder, with zero within-step angle increments. Residual is `(predicted_acceleration - observed_difference)*[1,1,5,5]`; minimize total squared residual across selected pairs. Bounds are independently [-16,16] m/s for each wind component, not a 16 m/s norm bound. First fit uses seven starts: (0,8) and six magnitude-8 vectors at angles 0,60,...,300 degrees. Later fits warm-start only the previous fitted vector. SciPy `least_squares(max_nfev=35,diff_step=1e-3)` per start; this is not a guaranteed 35 total derivative-call budget. Choose minimum squared residual; logged residual is its Euclidean norm, not RMS. The fitted vector stays constant inside each candidate rollout.

`r8_model.py:48-68`: initialize physical state from current raw state, accumulate every actual normalized command through the exact scale/floor/clip rule starting from zero to restore actuator setpoints, restore current frame, and rebuild policy memory from causal observations and commands. Each candidate checks bitwise equality of its reproduced current action to actual a_t. Candidates share causal starting history but have independent physical continuations. Future observed vessel positions use q(t)+k*v(t), current valid observations only; future model observations retain 1000 m range. Real future turns, scenario seeds, actual wind and environment RNG are not model inputs.

## Candidate protocol, cost, ties and fallback

`r8_planner.py:33-73`, `r8_model.py:62-90`: first allowable evaluation t=10; prediction activates only if a valid observed target is strictly within 600 m. While t<until, retain held reference without re-evaluation. Otherwise, when t>=next_plan, fit wind and evaluate H=60 one-second steps. Main period/hold=15 s; hold60 uses period/hold=60 with the same H. Changing period also changes future warm-start fit history, so this is not a single-factor horizon ablation.

Fixed candidate order is nominal, continue if a current reference exists, turn-90, turn-45, turn45, turn90. Side references lie 350 m from current boat position, rotated relative to the nominal-reference bearing. Nominal follows shared AvailabilityRelay feedback throughout. Non-nominal candidates initially hold, then restore that ordinary feedback at k>=hold; at release its incumbent is cleared. At k=0 each candidate uses the same previously computed action. Prediction stops at 60 s, original final-goal distance <=10 m, integration failure, or predicted NoRoute/NoLocalTarget error. A terminal arrival before 60 s is accepted, not considered incomplete.

At each segment, margin is minimum of static center-to-own-segment distance minus static entity radius minus60, and synchronous relative boat/vessel segment distance minus85. Feasible means `valid and not integration_failed and min_margin>=30`. No probabilistic validity or error bound is encoded. Score is final predicted distance to original mission goal +20 m for non-nominal +10 m for a side reference. If nominal feasible, stop evaluating and choose it. Otherwise choose feasible minimum score. Exact score ties preserve enumeration order. If none feasible, choose valid/non-integration-failed maximum (min_margin,-score), again first occurrence on exact tie. If no such rollout exists choose continue if present, else nominal. This last return is explicitly not a safety guarantee. No separate side-reference point-clearance prefilter exists; feasibility is assessed by predicted execution. Base planner failure before candidate construction propagates to the real runner.

## Shared endpoint manager and actual evaluation

`r8_planner.py:10-31`: only when the final goal is currently occupied in static-plus-current-dynamic circle map, keep a current reference if more than100 m away and its segment/point are clear. Otherwise enumerate eight references on a305 m ring around the final goal (0,45,...,315 degrees). Reject points <200 m from boat, non-clear segments, or point safety margin <120 m. Minimize distance from boat +80*absolute heading turn (radians); ties preserve ring enumeration. No feasible reference raises NoRouteError. When goal becomes clear, clear incumbent and reconnect ordinary relay. This shared task manager does not stop the boat or remove an obstacle. Relay settings are margin120, lookahead500, handoff100, trigger_clearance80 (`r7_dynamic.py:61-68`).

`r7_dynamic.py:13-15,37-40`, `run_r8.py:56-65,84`: dynamic entity radius25 m is own10+target15, counted once; safety buffer60 gives exclusion85. The true metric uses all actual targets, even outside observation range, and same-time relative linear segments over each second. Static exclusion is entity radius+60. Entity contact (`min_entity<=0`) terminates. Buffer invasion need not terminate immediately; subsequent NoRoute can do so. Arrival means distance to original goal <=10 m. Safe completion requires arrival AND strict minstatic>0 AND strict mindynamic>0; zero boundary margin is not safe. Do not describe avoidance of a buffer invasion as an observed reduction in entity collisions. The metric is a circular/linearly interpolated proxy, not exact swept hull or continuously integrated minimum distance.

## Inherited provenance and publication boundary

`docs/OBSTACLE_PROTOCOL.md`, `docs/obstacle_candidate_identity.json` identify the18D PART5 `saclstm_s14obst_noise_0204@10800` actor/normalizer. Source snapshot comes from read-only SOURCE_ROOT `/home/ot/Students/hs/sailboat-research/sailboat_RL/PART5/SAC-LSTM-att/`; copied checkpoint evidence originates from SOURCE_ROOT `runs/asset_0204_review/snapshot` and the user-provided archive recorded in identity JSON. Verified current actor SHA256 `6092d4543c003793f4cd3f21c5ed722f0978eebfdba2f62d77892af333085bd6`; normalizer `3baf7d1d9d4c9e4505fc991f339221e9e0dc64e9777c6f1c568413a2846b63b6`. Dynamics source SHA256 `8668f769194b65857667b255eeca6467e45d3e248131ea46af245bfbdc156313` is enforced by continuous.py.

`docs/UPSTREAM_MANIFEST.md` says no standalone LICENSE/COPYING file was found in the examined inherited tree. This audit likewise found no such top-level/project-depth-three file in NEW_ROOT; it is not an exhaustive public-web legal search. Identity and internal access do not establish public availability, redistribution permission, original training reproducibility, formal author attribution, or permission to publish weights/code. These remain unresolved author checks. Describe assets as inherited research assets; do not invent an open-source claim or a new license grant. No permission inference is needed for this internal evidence-only manuscript draft.
