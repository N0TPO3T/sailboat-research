# Project Memory

Durable project knowledge that may affect future research or engineering decisions.

Do not use this file as a session log, changelog, or experiment diary. Revalidate entries when the environment, implementation, dataset, or evaluation protocol changes.

---

## Canonical environments self-register from the repository

**Tags:** `environment`, `gymnasium`, `registration`, `reproducibility`

**Conclusion**

Importing `sailboat_rl` registers the canonical `sailboat-s14-nowind` and `sailboat-s14-wind` IDs from repository-owned code. Do not copy environment files into site-packages or add registrations to an external Gymnasium installation.

**Evidence**

- `sailboat_rl/__init__.py` owns the two Gymnasium registrations.
- `tests/test_canonical_core.py` constructs both IDs, resets them and executes steps.
- The same test compares fixed-seed one-step outputs against the pre-extraction environment sources.

**Implication**

Always `import sailboat_rl` before `gym.make(...)` and run the canonical smoke test before an expensive job. Obstacle environments are not registered by the canonical package.

---

## Canonical package training uses one explicit master seed, but resume is practical rather than bitwise simulator continuation

**Tags:** `seed`, `randomness`, `environment`, `training`, `evaluation`

**Conclusion**

The current `sailboat_rl.training` entries seed Python, NumPy, Torch CPU/CUDA, noise RNG and Gym spaces from one master seed; environment worker `i` uses `master_seed + i`. Strict deterministic Torch algorithms are an opt-in diagnostic because they can reduce performance or reject kernels. A resumed process restores learner/replay and main/noise RNG, but intentionally starts fresh environment episodes; it does not continue live simulator trajectories bit-for-bit.

**Evidence**

- `sailboat_rl/training/runtime.py` implements master/worker seeding and RNG capture/restore.
- All three canonical training entries apply the same worker rule and record it in `run_manifest.json`.
- Resume tests compare the restored Python/NumPy/Torch/noise RNG streams and replay sampling exactly.
- Historical `PART4/SAC/parll_lstm_normal.py` still seeds only Torch/CUDA and therefore retains the older reproducibility gap.
- The formal seed evaluator explicitly calls `random.seed`, `np.random.seed`, and `torch.manual_seed` per episode, so its evaluation protocol is stronger than the training scripts' seed handling.

**Implication**

Use the manifest master seed as the run identity and preserve the evaluator's explicit per-episode seeding. Do not claim cross-machine bitwise equality or uninterrupted-vs-resumed trajectory equality, because VecEnv/simulator state is deliberately not serialized.

---

## Canonical paths are working-directory independent; historical paths are not

**Tags:** `checkpoint`, `paths`, `training`, `evaluation`

**Conclusion**

Canonical modules use package imports and resolve default outputs under repository-root `canonical_runs/`. Historical `PART4/PART5` scripts still save/load relative to the process working directory and retain their original bare imports.

**Evidence**

- Canonical SAC/SAC-LSTM receive an explicit `model_dir` from the training entry point.
- Canonical training defaults to `canonical_runs/model/` and `canonical_runs/runs/`.
- The original experiment scripts still use relative `./model` and `runs/`.
- variant READMEs explicitly recommend `cd` into the experiment directory before running.

**Implication**

Prefer `python -m sailboat_rl...` for new work. When reproducing a historical experiment, still run from its intended directory. Evaluation must always resolve the exact actor/Q/normalizer triplet.

---

## Canonical model snapshots and resumable training checkpoints have different contracts

**Tags:** `checkpoint`, `training`, `resume`, `SAC`

**Conclusion**

`agent.save/load` remains the stable evaluation snapshot format and contains actor, Q critic and state normalizer only. Each canonical run additionally writes atomic resumable checkpoints containing actor, Q/target Q, normalizer, adaptive alpha, optimizer states, counters, valid replay/PER state and main/noise RNG. Resume is a practical learner continuation: environments and online recurrent state/history are reset in the new process.

**Evidence**

- End-to-end smoke training saved and reloaded all three model families from a non-repository working directory; evaluation snapshot actor, Q critic and normalizer matched exactly.
- FC and LSTM resume regression tests compare every saved learner/replay field and continue finite optimizer updates after recreation.
- A real FC `SIGTERM` produced a checkpoint at a safe train-loop boundary, and a new process continued updates from that checkpoint; both FC and LSTM training entries have completed cross-process resume.
- Full-capacity replay round-trips were measured at `1e6` entries for both replay schemas.

**Implication**

Use model snapshots for evaluation and run checkpoints for training resume. Never substitute one for the other. Do not claim bitwise simulator continuation: live VecEnv/ODE state and SAC-LSTM online hidden/history are intentionally absent, so resumed workers begin fresh episodes while replay training sequences remain intact.

---

## Wind information and temporal history have measured but different robustness limits

**Tags:** `SAC`, `LSTM`, `wind`, `evaluation`, `baseline`

**Conclusion**

Under the committed 10,800-episode seed evaluation, explicit wind observation (SAC-wind) and history (SAC-LSTM without wind observation) both greatly outperform memoryless SAC-nowind under random wind. LSTM nearly matches explicit wind observation on random wind, but retains a clear gap on fixed adverse 150°/180° winds; memoryless SAC-nowind fails completely there.

**Evidence**

`PART4/seed_reward_ablation/seed_eval_suite/seed_eval_results/seed_eval_20260518_002624/` contains episode data, manifest and aggregate tables for two checkpoints per model family with 3% sensor/actuator noise:

- random wind: SAC-wind 94.65%, SAC-LSTM 93.65%, SAC-nowind 43.60%;
- fixed 150°/180°: SAC-wind 99.50%/93.75%, SAC-LSTM 82.75%/82.75%, SAC-nowind 0%/0%.

**Implication**

Use SAC-wind as the strongest current robustness reference and adverse fixed wind as a discriminative test. Do not claim that LSTM fully reconstructs missing wind information. Revalidate after environment, checkpoint, or evaluation changes because checkpoints are not stored in Git.

---

## Dense progress reward is the only component with a demonstrated collapse in the current reward ablation

**Tags:** `reward`, `ablation`, `checkpoint`, `evaluation`

**Conclusion**

In the committed step-8400 reward-ablation batch, removing dense progress/speed collapsed success to 1.2%, while the available no-action, no-checkpoint and no-arrival variants remained at 98.0%, 99.7% and 99.6%. This supports dense progress as essential for those trained checkpoints, but does not prove the other components are generally unnecessary.

**Evidence**

`PART4/reward_ablation_new/test_results_batch/20260521_163928/summary.md` reports 1000 episodes per available variant with 3% sensor/actuator noise. The summary has no matched baseline and no no-penalty row. `PART4/reward_ablation_new/README.md` also records that final training statistics may say 9e6 steps while the latest real actor/Q/normalizer files stop at step 8400.

**Implication**

Do not remove dense progress without a replacement learning signal. Do not fabricate or request a step-9000 checkpoint from final-stats metadata; use the latest complete matching triplet that actually exists. Treat conclusions about the other reward terms as protocol-specific until a matched baseline and missing variant are evaluated.
