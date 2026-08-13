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

## Training `--seed` is not full determinism in the canonical scripts

**Tags:** `seed`, `randomness`, `environment`, `training`, `evaluation`

**Conclusion**

The canonical PART4 training scripts seed Torch and pass a seed to `env.reset`, but they do not seed Python `random` or global NumPy. The environments use `random.uniform` for initial wind/heading/state and `np.random.randn` for Dryden turbulence. Therefore a training label such as `seed=100` does not by itself guarantee a reproducible trajectory distribution.

**Evidence**

- `PART4/SAC/parll_lstm_normal.py` seeds Torch/CUDA but has no `random.seed` or `np.random.seed` call.
- `gymnasium/envs/sailboat/sailboat_s14.py` uses module-level `random` and `np.random` after `super().reset(seed=seed)`.
- The formal seed evaluator explicitly calls `random.seed`, `np.random.seed`, and `torch.manual_seed` per episode, so its evaluation protocol is stronger than the training scripts' seed handling.

**Implication**

Do not interpret training-seed comparisons as deterministic replications without first fixing or measuring this gap. Preserve the evaluator's explicit per-episode seeding when modifying evaluation.

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

## Canonical checkpoints are evaluation snapshots, not full resume state

**Tags:** `checkpoint`, `training`, `resume`, `SAC`

**Conclusion**

Canonical SAC-FC and SAC-LSTM checkpoints save actor, Q critic and state normalizer only. They do not save target critic, adaptive alpha/log-alpha, optimizer states, replay contents or training counters.

**Evidence**

- End-to-end smoke training saved and reloaded all three model families from a non-repository working directory; actor, Q critic and normalizer matched the written files exactly.
- `SAC_fc_continuous.save/load` and `SAC_lstm_countinuous.save/load` contain no serialization for the omitted state.

**Implication**

The current format is sufficient for deterministic evaluation but cannot provide an exact training resume. Do not claim alpha/optimizer restoration or exact continuation without an explicit future checkpoint-format change.

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
