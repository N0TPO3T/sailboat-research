# Isolated 0204@10800 obstacle candidate

This is an 18D PART5 attention candidate, not a replacement for the existing 14D fourth-chapter baseline. No training, official 300-episode batch, or performance result is implied. Experiments and tests are centrally run by the main agent; this assignment wrote but did not execute them.

## Entry and physical implementation

Audited SOURCE_ROOT `/home/ot/Students/hs/sailboat-research/sailboat_RL/PART5/SAC-LSTM-att/{modeltest_noise,batchtest,SAC_lstm_att_normal,utils_lstm_att_normal,noise_utils,globals}.py` and `sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_V3.py`. The modeltest and batch entries request `sailboat-s14-obst-v3`, prefix `saclstm_s14obst_noise_0204`, checkpoint 10800, width 256. `sailboat_RL/gymnasium/envs/sailboat/__init__.py:14` exports that file's `Sailboat_obst_v3`. SOURCE_ROOT's `.venv/.../gymnasium/envs/__init__.py` contains no registration for that ID: the complete original historical Gym installation cannot be certified from this repository. The candidate explicitly loads the audited class directly, not by a guessed Gym registry, and records this limitation in its manifest. No `research/chapter5_static` Aligned layer is loaded.

The physical class is self-contained (NumPy, pygame, Gymnasium, SciPy); force coefficients/mass parameters are embedded, with no external dynamics tables. The isolated runtime imports only Actor/normalizer utility, noise, globals, original SAC module for the reference method, and this physical file. Original test scripts are audit evidence, not imported: their CLI, plotting, SB3, critic load and learner/replay creation are avoided. Original `select_action` is invoked unmodified as an unbound method against actor/normalizer/device only. No source-directory import or execution occurs.

## Observation, normalization, history and units

* `[0:8]`: world x,y (m), roll phi and heading psi (rad), body u,v (m/s), p,r (rad/s).
* `[8:10]`: actual sail/rudder feedback angles (rad).
* `[10:12]`: previous-to-current reduction in goal distance and absolute x-distance (m).
* `[12:14]`: goal world coordinates (m); original goal (500,0).
* `[14:18]`: **four scalar slots, not four obstacles**: distance1 (m), bearing1 relative to heading (rad), distance2, relative bearing2. Missing pairs are `(0,0)`. V3 detections have 150 m range and 120-degree total FOV (the stale method comment says 90 degrees); previously detected obstacles remain remembered, then the two nearest within 150 m are selected. Reset returns all four slots zero, even if obstacles are nearby; first detection happens after a step.

Frozen normalizer: `(x-mean)/(sqrt(var)+1e-6)`, including both previous and current noisy observations. Strict actor load uses `weights_only=True`; normalizer fields/dimension/finite values/nonnegative variance/positive count are checked. No statistics updates or optimizer exists.

Persistent single-step Actor receives previous noisy observation, previous **raw normalized Actor action** (not noisy or physical action), current noisy observation and `env_ids=['v0']`. Reset seeds previous observation with initial noisy observation, action zeros, clears h/c and attention history. Each forward advances h/c once; LN LSTM outputs enter a 10-slot deque initialized to zeros. Deterministic action is `tanh(mu)`, but original scripts never call `eval()`: dropout p=.1 remains active in history FC, current FC, attention weights and final FC. Explicit `legacy_training` retains this behavior, frozen parameters notwithstanding; `eval` disables dropout and is a deliberate variant, not the original-script protocol.

Noise is copied unchanged: sensor ratio .03 with feature-specific clipping, heading/bearings wrapped; actuator noise receives normalized Actor action and physical high=pi/18, then Action_adapter multiplies noisy output by high. Internally actuator noise multiplies by high to work in radians, applies deadzone/quantization/execution error, divides by high and clips back to [-1,1]; the final Action_adapter multiplication therefore yields radians, not a double scaling bug. Sensor RandomState uses seed and actuator RandomState uses seed+1000, independently of Dryden global NumPy. V3 then floors physical increments to whole degrees using `// (pi/180)` (negative floor asymmetry retained), clamps target sail/rudder, and applies rate-limited actual changes over a one-second physical step. Do not rescale through the known unit-wrong Aligned implementation.

## Explicit adaptations and original limitations

`ObstacleSegment` wraps untouched V3. It provides independent global Python/NumPy RNG states per instance: original `reset(seed)` seeds Gym but heading uses Python global random and Dryden uses global NumPy. Paired runs restore identical streams before each simulator call. Wind overrides initialize all wind globals after original reset; fixed no-obstacle/simple static scenes override original hardcoded seven-point map. These are recorded scenario adaptations, not claims that original scripts already honor CLI wind/seed correctly. Original V3 reset/step implementation remains byte-identical. Constructor/reset and initial zero obstacle slots are preserved.

No necessary dynamics interface repair has been applied. Interface numerical exceptions, integration hangs and nonfinite observations are retained as failures. Successful Actor parity does not validate checkpoint policy competence. A shared failure in both physical paths only establishes migration parity. Candidate adoption remains the main agent's decision.

## API and same-forward feature schema

`loading_paths()` returns absolute snapshot/actor/normalizer paths. `protocol_manifest()` returns loaded protocol plus SHA256 for each snapshot/asset. `CandidateModules.paths` returns actual module files. All are under NEW_ROOT.

`ObstacleController(mode='legacy_training'|'eval')`: `actor`, `normalizer`, `modules`, `previous`, `previous_action`, `steps`, `_capture`; `reset(obs18)`, `act(obs18, record_features=False)` returns the existing `Decision(action, features, history_steps)`; `hidden()` returns h/c; `history()` additionally returns attention-history values; `close()` removes the hook. Env id is `v0`. Features schema is **274 float values**: frozen-normalized current noisy observation18 followed by the 256D `lstm_ln` output from that exact decision forward. Hook capture does not issue a second forward or advance memory. Compatible one-step interfaces do not constitute a continuous-goal 18D implementation.

Under a rigid world translation/rotation, obstacle distances and heading-relative bearings are invariant: leave all four scalar slots unchanged (including missing zeros), transform x/y and goal jointly, adjust heading consistently, and do not rotate body velocity again. A complete causal re-encoding must recompute historic goal-progress features with the chosen goal and preserve per-time relative obstacle pairs; world map centers transform separately. Normalizer remains frozen.

## Commands and bounds

From any working directory, using NEW_ROOT's interpreter:

```sh
N=/home/ot/Students/hs/sailboat-routing-v0
$N/.venv/bin/python -B $N/scripts/evaluate_obstacle_candidate.py --phase parity --mode legacy_training --max-wall-seconds 120
$N/.venv/bin/python -B $N/scripts/evaluate_obstacle_candidate.py --phase parity --mode eval --max-wall-seconds 120
$N/.venv/bin/python -B $N/scripts/evaluate_obstacle_candidate.py --phase pilot --mode legacy_training --max-steps 1000 --max-wall-seconds 120
$N/.venv/bin/python -B $N/scripts/evaluate_obstacle_candidate.py --phase capability --mode legacy_training --scenarios 8 --max-steps 1000 --max-wall-seconds 600
$N/.venv/bin/python -B -m pytest $N/tests/test_obstacle_candidate.py
```

Parity: 16 fixed observations, then up to 32 paired true V3 physical steps at 90 degrees with one static obstacle. Common torch RNG is restored for each paired decision, including legacy dropout. Compare action/h/c/LN attention-history absolute errors <=1e-6, physical raw state <=1e-5, and equal termination. Tolerances are declared before execution and can only be tightened. Partial parity output is retained if interrupted.

Pilot: exactly one no-obstacle 0-degree episode. Capability: this same first episode is the timing pilot, then seven remaining fixed cases, ordering no obstacles at 0/90/150/180, then one obstacle (190,10) at those four angles; one configurable seed shared across all scenes. Scale is at most 8 scenes (not 300); every scene <=1000 steps. Start with one seed; additional seeds require separate explicit bounded invocations, not a search. One CPU/thread, total wall <=600 s including integrator via Linux SIGALRM. No remaining scene starts before first pilot finishes. Estimated single-case cost is **not yet measured**; cap a first pilot at 120 s, use its recorded wall_seconds to estimate later batches (at most remaining total wall). SIGALRM may have small delivery latency inside a native call; it is a cooperative Unix hard deadline, not an OS kill supervisor.

Every run exclusively creates a new directory under NEW_ROOT/runs (existing output is rejected). results.json includes all completed success/failure records, wall time, modes/noise, exceptions and not-started cases. JSONL saves initial state and each completed true transition, raw/physical actions, reward/time and safety margin. No failed old JSON is overwritten or removed.

Safety distance uses true world-position samples and line segments between one-second endpoints to full fixed map centers, minus original 40 m collision threshold, including initial position; it is not based on noisy visible slots. This improves over endpoint-only checks but **does not recover curved sub-second integration paths or a ship hull footprint**, and is not a formal collision-free certificate. Original termination checks center distance at action endpoints; geometry alone cannot guarantee actual low-level safety.

## Byte-copy manifest

All source SHA256 were separately computed after copying and match the destination values below; no upstream writes. Assets are copied from NEW_ROOT/runs/asset_0204_review/snapshot (actor/normalizer only, no critic).

| file (third_party/obstacle_candidate unless asset) | SHA256 |
|---|---|
| batchtest.py | 8af71a63ff4066e9c99cfc187737d143c68d2027e350cd04633fe8f1499cc26f |
| globals.py | 8bd1556d65ff15614341105b9479cdbbb259a3d0239e795ae598699ca86bd41f |
| modeltest_noise.py | 337e08ea53b219bf4ebfc2dc8713874e63851d22c45238fb488a0f4dfd3d85a0 |
| noise_utils.py | f94dabc254a8eca8bb3b35d07943b8c644bcd73c21b389e796b600e26c1faf1c |
| SAC_lstm_att_normal.py | e2a7d72d094aa9c47294fd8d4da66129b7ab3b0f6fd96f5a206b40924acc67e3 |
| sailboat_s14_obst_V3.py | de684a457137798673be7158133ab89e047c4e839a506086f515957d08fc91d7 |
| utils_lstm_att_normal.py | ff2e43e2ea40030b2c3eff44649fd9b59306dd0d042d9b0093e6584f8c0fd513 |
| checkpoints/obstacle_candidate/saclstm_s14obst_noise_0204_actor10800.pth | 6092d4543c003793f4cd3f21c5ed722f0978eebfdba2f62d77892af333085bd6 |
| checkpoints/obstacle_candidate/saclstm_s14obst_noise_0204_normalizer10800.pth | 3baf7d1d9d4c9e4505fc991f339221e9e0dc64e9777c6f1c568413a2846b63b6 |
