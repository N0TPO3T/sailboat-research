# Upstream migration manifest

## Identity and scope
- SOURCE_ROOT: `/home/ot/Students/hs/sailboat-research` (read-only).
- NEW_ROOT: `/home/ot/Students/hs/sailboat-routing-v0` (independent sibling).
- Upstream HEAD: `b079399bfeb659c228156f767962374f95f56614`; pre-existing uncommitted changes are preserved, not committed or reverted.
- Inventory: `runs/audit/upstream_files_before.json` (1351 files, 1,235,018,876 bytes); Git status before migration: `runs/audit/upstream_git_status_before.bin`. Inventory excludes `.git`, `.venv`, `__pycache__` trees; do not claim those trees were fully content-hashed.
- Selected checkpoint: fourth-chapter 14-dimensional `saclstm_s14nowind_buf1e6_seed100@7200` Actor + its normalizer. Existing exact-asset entry is `research/smoke_baseline.py`; NOT the official evaluator's default `saclstm_s14nowind_final@9000`, and not a fifth-chapter model. Original training provenance and final paper identity remain unverified.
- Environment: the exact `sailboat_RL/gymnasium/envs/sailboat/sailboat_s14.py` used by that existing entry. The PART4/SAC same-named file differs and is not silently substituted. Runtime does not import the engineering environment.
- Primary A capability protocol extends the existing no-additional-noise smoke to complete 500 m episodes; native Dryden wind remains. The separate noise-enabled parity check validates the original optional noise path but is not evidence about the checkpoint's original training settings.

## Unmodified copies
Source paths are relative to SOURCE_ROOT, target paths to NEW_ROOT. Copies use separate files, not hard links or code symlinks. All author comments remain intact. No standalone LICENSE/COPYING file was found in the examined inherited tree; no new license grant is implied.

| Source | Target | Purpose | SHA256 |
| --- | --- | --- | --- |
| `sailboat_RL/PART4/SAC/globals.py` | `third_party/senior/globals.py` | unmodified runtime snapshot | `8bd1556d65ff15614341105b9479cdbbb259a3d0239e795ae598699ca86bd41f` |
| `sailboat_RL/PART4/SAC/utils_lstm.py` | `third_party/senior/utils_lstm.py` | unmodified runtime snapshot | `311b0343582cd873922cedf2db23cc0d786a7062646657326ad0bbde90a05ab4` |
| `sailboat_RL/PART4/SAC/noise_utils_nowind.py` | `third_party/senior/noise_utils_nowind.py` | unmodified runtime snapshot | `0c69bb7ef1aa50aa43df90c176d95bf140c5c5d3d500b1f8c4f84c83ceee8514` |
| `sailboat_RL/gymnasium/envs/sailboat/sailboat_s14.py` | `third_party/senior/sailboat_s14.py` | unmodified runtime snapshot | `8668f769194b65857667b255eeca6467e45d3e248131ea46af245bfbdc156313` |
| `model/saclstm_s14nowind_buf1e6_seed100_actor7200.pth` | `checkpoints/actor.pth` | selected frozen checkpoint asset; ignored by Git | `c8cc1bc335c5bd4bfeed9100f5903e6d2849e35db9da3ea1a035fbbbe6f9e739` |
| `model/saclstm_s14nowind_buf1e6_seed100_normalizer7200.pth` | `checkpoints/normalizer.pth` | selected frozen checkpoint asset; ignored by Git | `1de337a2b66452554f691d23d9a2fc4d622970c9b94426349543b0f8f22d3097` |
| `sailboat_RL/PART4/SAC/SAC_lstm.py` | `runs/audit/reference/SAC_lstm.py` | read-only isolated comparison source; not a runtime dependency | `7f09ef4c1400df5cdba724d9de7358941e59b252ea9f3de0939714c79cfdbe94` |
| `sailboat_RL/PART4/SAC/test_eval_lstm.py` | `runs/audit/reference/test_eval_lstm.py` | read-only isolated comparison source; not a runtime dependency | `2684be680e050e36e20f9d684cf3821b6b8ea895a30a9315a916058a9572d80d` |
| `research/smoke_baseline.py` | `runs/audit/reference/smoke_baseline.py` | read-only isolated comparison source; not a runtime dependency | `1897dbb23714c40add4e9cd5139102af52a8203a52efeb16a6e2333841632930` |

The four runtime sources also have byte-identical isolated comparison copies under `runs/audit/reference/`. The comparison extracts and executes the original `select_action` method from its copied AST without constructing a learner, optimizer or replay. Reference-only files and selected weights are not committed. `utils_lstm.py` retains its original unused Critic declarations to preserve the source snapshot byte-for-byte.

## Audited contract
- Observation: world x/y metres; roll/heading radians; body u/v m/s; roll/yaw rates rad/s; actual sail/rudder radians; distance progress and absolute-x progress metres; world target x/y metres. No true wind enters the 14D Actor observation.
- Actor: `Actor(14,2,(256,256))`, deterministic `tanh(mu)`, eval mode and frozen parameters. Frozen normalizer `(x-mean)/(sqrt(var)+1e-6)` loaded strictly; no online statistic update.
- Online history is persistent single-step h/c, not a sliding 10-step window. Training seq_len=10/BPTT=10 must not be mistaken for online reset. First previous observation equals the initial observation and previous action is zero. Later history pairs the previous observation with the original normalized command, not actuator-noised radians.
- Optional inherited actuator noise accepts/returns normalized commands; `Action_adapter` scales by action_space.high (pi/18). Environment applies signed floor to one degree, accumulates targets, clips sail/rudder targets and rate-limits the physical response. No unit correction or quantization change is made to inherited code.
- One action advances simulation by one second, using the original adaptive Dormand-Prince integration (initial 0.05 s, not a fixed 20-step integrator). Original terminal radius 10 m, boundary radius 750 m, time limit 1000 s retained for A.
- Native wind is updated after a physical transition; labels logged there are the next decision's current wind, not the preceding action's wind. Future C data must align at the decision boundary. The vector construction is a world-frame velocity/blowing-toward convention; evaluate physical interpretation against the force formula before planning with it.
- `gym.reset(seed)` alone does not seed the source Python/global NumPy generators. A explicit scenario seed covers both; the adapter saves/restores per-instance RNG state. Fixed mean wind is set once after reset, not at each action; Dryden evolves normally.
- The optional feature hook captures the same forward's `lstm_ln` output (256D) plus current normalized observation (14D). It never performs a second Actor forward. No env/info/true-wind object is exposed to this hook.

## Necessary adaptations (outside inherited files)
`src/sailboat_routing/runtime.py` loads copied source modules under isolated `globals`, avoids Gym registry collision, enforces CPU/single-thread execution and NEW_ROOT-only source paths, requires the matching normalizer, freezes Actor parameters, and offers a same-forward feature capture. Scenario RNG isolation and fixed initial mean wind make the bounded comparison repeatable; they do not alter ODE equations. Runtime assets are renamed actor.pth/normalizer.pth with the SHA256 above. All inherited runtime files are byte-identical copies.

## Dedicated environment
Independent NEW_ROOT `.venv`, created with `/home/ot/miniconda3/bin/python -B -m venv`; no system-site-packages, old editable install, or source environment copy. Packages are installed only in NEW_ROOT; all pip cache/temp/Matplotlib paths are inside NEW_ROOT. Python 3.13.11 uses the shared interpreter/standard library read-only; PyTorch 2.13.0+cpu, NumPy 2.4.6, SciPy 1.18.1, Gymnasium 1.3.0, Pygame 2.6.1 and Matplotlib 3.11.1 are separately installed. Exact dependency lock is saved after successful import/installation. No CUDA job, learner or training is started.
