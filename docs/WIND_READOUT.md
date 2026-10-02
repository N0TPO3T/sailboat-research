# Causal local-wind readout

## Status and information boundary

This is an independently usable mathematical module, not a claim of real-wind accuracy. Stage B currently reports `passed: false` (5/6). No new capture, fitting, Actor training, or readout performance experiment was run. The production fitting CLI always checks `runs/stage_b/result.json` and refuses to fit unless its `passed` field is exactly JSON `true`; there is no bypass flag. Synthetic Python API checks are only numerical checks, never real wind evaluation.

The Actor and its normalization remain frozen. Production features are **270** entries in this order: current frozen-normalized 14-dimensional observation, followed by the **256-dimensional `lstm_ln` output from the same current Actor forward**. Features must be captured before applying the current action and cannot include the observation after it. Wind labels are only available to the offline fitter/evaluator. Online prediction takes only features, frame angle and history count: no environment, info dictionary, wind query, seed, oracle angle or wind speed. No capture implementation is included here.

All directions are **blow-toward radians**, not meteorological blow-from bearings. Frame angle is the world orientation of the local x axis. World = wrap(local + frame angle); local = wrap(world - frame angle). The functions `local_to_world`, `world_to_local`, and `wrap_angle` operate on scalars or arrays.

## Complete input format

Keep data and manifests inside `/home/ot/Students/hs/sailboat-routing-v0` (NEW_ROOT). One NPZ file is one complete episode. Use non-object arrays; loading has `allow_pickle=False`. The exact NPZ field whitelist is:

| Field | Shape/type | Meaning |
|---|---|---|
| `metadata_json` | scalar Unicode JSON string | metadata below |
| `features` | finite numeric `(N,270)` | observation14 + same-forward lstm_ln256 |
| `labels_local_rad` | finite numeric `(N,)` | true local blow-toward angle at this decision; offline only |
| `decision_time` | finite numeric `(N,)` | physical decision timestamps, strictly increasing |
| `labels_time` | finite numeric `(N,)` | exactly equal to decision_time, not next-step timestamps |
| `observed_through_time` | finite numeric `(N,)` | latest physical observation used in each feature; must be <= decision_time |
| `frame_angle` | finite numeric `(N,)` | current world orientation of the local frame |
| `history_count` | nonnegative integer `(N,)` | count of causally available historical observations before decision |
| `goal_switch` | boolean `(N,)` | true at first decision with the changed target/frame |
| `wind_change` | boolean `(N,)` | externally marked true wind-change onset, evaluation only |

Metadata uses **exactly** these keys:

```json
{
  "schema_version": 1,
  "episode_id": "train_episode_001",
  "scenario_id": "train_scenario_001",
  "feature_timing": "decision_pre_action",
  "source_identity": {
    "actor_sha256": "<64 lowercase hex characters of the actual frozen Actor file>",
    "normalizer_sha256": "<64 lowercase hex characters of the actual frozen normalizer file>",
    "feature_schema": "frozen_obs14+lstm_ln256_pre_action_v1"
  }
}
```

The digest placeholders are explanatory, not valid data. The capture author must attest `decision_pre_action` and fill observed-through times from actual capture provenance. The loader rejects unknown fields, post-action timing, future observations, label misalignment, wrong dimensions and mixed source identities. Timestamp and digest declarations cannot prove an unaudited producer honest: independently audit the capture path before accepting real data. Existing files without these attestations are **not** silently trusted or converted. The 14D frozen normalization and separate readout feature normalization are different artifacts.

Predeclare the JSON manifest **before collecting/fitting**, with exactly this structure:

```json
{
  "schema_version": 1,
  "splits": {
    "train": ["train_episode_001"],
    "validation": ["validation_episode_001"],
    "test": ["test_episode_001"]
  }
}
```

Each split must be nonempty, every supplied episode must occur exactly once, and no scenario can occur across different splits. Multiple complete episodes of a scenario may occur within one split. Missing, repeated, unassigned or cross-split IDs are rejected. Never split neighboring frames randomly. The CLI checks the manifest but cannot establish when it was declared; keep the original predeclaration as provenance.

## Fit and deployment semantics

`RidgeWindReadout.fit(features, labels_local_rad, *, alpha, source_identity)` is the mathematical fitter. Call it with **train rows only**. The CLI includes only train rows with `history_count >= warmup`. It computes population mean/std on those rows; constant columns use scale 1. Labels become `(sin(angle), cos(angle))`. Centering gives an unpenalized intercept; a primal/dual closed-form solve uses a positive ridge penalty on coefficients only. Generic dimensions are supported by the Python fitter for numerical tests; production loading enforces 270 by default.

`predict_vectors(features)` takes an N-by-D matrix and outputs N-by-2 sin/cos vectors. `CausalWindFilter(model, *, warmup=10, min_norm=1e-6, ema_weight=0.25)` owns one episode's EMA state. Call `update(feature_vector, *, frame_angle, history_count)` exactly once per chronological decision. It returns `WindEstimate(local_rad, world_rad, valid, vector_norm)`. Start a new filter for each episode. Do not reset it solely because a target frame rotates.

Insufficient history or tiny predicted vector norm returns `valid=False` and NaN directions. The vector norm is only a degeneracy detector, **not confidence or probability**. Valid raw predictions are normalized to unit vectors, rotated to world coordinates, and combined in a causal world-frame sin/cos EMA. Only then is the result converted into the *current* local frame. Opposite-vector cancellation also returns invalid, retaining the prior filter state. Invalid inputs do not update the EMA or expose a stale estimate as current. The EMA uses no future window. The low-level stateful API requires the caller to preserve chronological order; `load_episode` checks timestamps and `predict_episode(model, episode, **filter_options)` visits the stored episode in order. The latter reads no labels and verifies frozen source identity.

Models use exclusive-create `save(path)` and strict `RidgeWindReadout.load(path, *, expected_source_identity=None, expected_dimension=None)`. NPZ fields are exactly `version`, `dimension`, `mean`, `scale`, `coefficients`, `intercept`, `alpha`, `source_identity_json`. Version is 1; output coefficients are D-by-2. Production deployment should supply both expected identity and expected dimension 270; wrong dimensions/identities, nonpositive scales, malformed arrays and unknown versions are rejected. Save cannot overwrite an existing model.

## CLI and metrics

After the real Stage B gate passes and audited complete episode captures exist:

```sh
cd /home/ot/Students/hs/sailboat-routing-v0
.venv/bin/python scripts/fit_wind_readout.py \
  --episodes runs/readout_capture/episodes \
  --manifest runs/readout_capture/splits.json \
  --alphas 0.1 1 10
```

Optional arguments are `--output`, `--warmup`, `--min-norm`, `--ema-weight`, `--window-steps`. The parameter whitelist is argparse's explicit options; there are no capture/env/oracle/gate-bypass parameters. At most 8 distinct positive alphas are accepted. Validation MAE chooses alpha (ties keep declared candidate order), never test performance. Each candidate uses the same train-only normalization. No train+validation refit occurs. **Test is evaluated only once**, after selection. Empty validation prevents selection. Test/event empty sets remain explicitly empty, not fabricated numbers.

All output paths resolve inside NEW_ROOT/runs; input paths must resolve inside NEW_ROOT too. Default output is a unique `runs/wind_readout/<UTC timestamp>_<suffix>` directory, containing `model.npz` and `result.json`. Existing output directories are refused. The result preserves source identity, all input episode file hashes, manifest hash and content, Stage B result hash, alpha candidates/validation metrics, selected alpha, test metrics and inference options. Missing data or a failed/missing Stage B gate returns exit status 2 and creates no fake metrics. The current default is intentionally **blocked by the failed Stage B gate**.

`circular_metrics(predicted_rad, labels_rad, valid=None)` reports shortest absolute circular error in degrees, frame-weighted MAE and P90, valid count and total count. Empty sets use `status: "empty"`, count 0 and null metrics. `evaluate_episodes` returns overall errors, goal-switch errors, and wind-change response errors. Each event window includes the flagged decision and the next W-1 decisions (default W=10), is truncated at episode end, and overlapping windows count each frame once. Invalid predictions are excluded from errors but retained in total-count coverage. These are post-event response **errors**, not claimed settling time or confidence calibration. There is no event inference from future values or fabricated wind-change marking.

## Independent verification interface

`tests/test_wind_readout.py` contains deterministic unittest coverage for circular wrap, ridge closed form/low sample/constant columns, train-only statistics, split leakage, future/misaligned timestamps, provenance whitelist, warmup/vector degeneracy, world-frame EMA under goal rotation, causal prefix invariance, model roundtrip/dimension/identity guards, and event windows bounded by episode. Tests were authored but **not run by this worker**, per assignment; the integration owner performs the final run.

For a throwaway synthetic smoke check, fit a small finite X and known angle y with `RidgeWindReadout.fit`, then call `CausalWindFilter.update`, `circular_metrics`, `save` and `load` inside a temporary NEW_ROOT/runs directory. Use valid-shaped synthetic identity hashes explicitly labeled synthetic. This exercises actual numerical code without environment access. Do not report its errors as real local wind or closed-loop evaluation. No real readout accuracy, wind-response performance or Actor/route benefit has been measured here.
