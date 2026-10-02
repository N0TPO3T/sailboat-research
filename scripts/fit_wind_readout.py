#!/usr/bin/env python3
"""Fit causal episode captures after evidence-bound interface admission, not a 100% success gate."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sailboat_routing.runtime import configure_cpu
from sailboat_routing.experiments import Budget
from sailboat_routing.admission import load_admission
configure_cpu()
import numpy as np
from sailboat_routing.wind_readout import FEATURE_DIMENSIONS, RidgeWindReadout, evaluate_episodes, load_episode, split_episodes


def _inside(path, root):
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"path must remain inside {root}: {path}")
    return resolved


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=Path, required=True, help="Directory of whole-episode *.npz files")
    parser.add_argument("--manifest", type=Path, required=True, help="Predeclared episode split JSON")
    parser.add_argument("--output", type=Path, help="New, nonexistent directory inside NEW_ROOT/runs")
    parser.add_argument("--admission", type=Path, default=ROOT / "runs/navigation_admission.json")
    parser.add_argument("--alphas", type=float, nargs="+", default=[0.1, 1.0, 10.0])
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--min-norm", type=float, default=1e-6)
    parser.add_argument("--ema-weight", type=float, default=0.25)
    parser.add_argument("--window-steps", type=int, default=10)
    args = parser.parse_args(argv)
    budget = None
    status = "failed"
    try:
        admission = load_admission(args.admission)
        gate_path = args.admission
        expected_source = admission["source_identity"]
        dimension = FEATURE_DIMENSIONS[expected_source["feature_schema"]]
        episode_dir = _inside(args.episodes, ROOT)
        manifest_path = _inside(args.manifest, ROOT)
        if not episode_dir.is_dir() or not manifest_path.is_file():
            raise ValueError("missing existing episode data directory or split manifest; no fake metrics generated")
        files = sorted(episode_dir.glob("*.npz"))
        if not files:
            raise ValueError("missing episode NPZ data; no fake metrics generated")
        for path in files:
            _inside(path, ROOT)
        if len(args.alphas) > 8 or len(set(args.alphas)) != len(args.alphas) or any(not np.isfinite(a) or a <= 0 for a in args.alphas):
            raise ValueError("alphas must be a small unique set (1..8) of positive finite values")
        if args.warmup < 0 or args.window_steps <= 0 or not np.isfinite(args.min_norm) or args.min_norm <= 0 or not 0 < args.ema_weight <= 1:
            raise ValueError("invalid warmup/window/min-norm/ema-weight")
        manifest = json.loads(manifest_path.read_text())
        episodes = [load_episode(path, dimension=dimension) for path in files]
        split = split_episodes(episodes, manifest)
        masks = [ep.history_count >= args.warmup for ep in split["train"]]
        features = np.concatenate([ep.features[mask] for ep, mask in zip(split["train"], masks)])
        labels = np.concatenate([ep.labels_local_rad[mask] for ep, mask in zip(split["train"], masks)])
        if not len(features):
            raise ValueError("training episodes contain no rows after warmup")
        source = split["train"][0].source_identity
        if source != expected_source:
            raise ValueError("episode features do not match the approved frozen control protocol")
        options = dict(warmup=args.warmup, min_norm=args.min_norm, ema_weight=args.ema_weight, window_steps=args.window_steps)
        budget = Budget("wind_readout_fit")
        candidates = []
        best_model, best_score = None, float("inf")
        for alpha in args.alphas:
            budget.check()
            model = RidgeWindReadout.fit(features, labels, alpha=alpha, source_identity=source)
            metrics = evaluate_episodes(model, split["validation"], **options)
            candidates.append({"alpha": alpha, "validation": metrics})
            score = metrics["overall"]["mae_deg"]
            if score is not None and score < best_score:
                best_model, best_score = model, score
        if best_model is None:
            raise ValueError("validation has no valid estimates; cannot select alpha")
        # Test is evaluated exactly once, AFTER selection; never used for refit or tuning.
        budget.check()
        test_metrics = evaluate_episodes(best_model, split["test"], **options)
        run_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
        output = _inside(args.output or ROOT / "runs" / "wind_readout" / run_name, ROOT / "runs")
        if output.exists():
            raise ValueError(f"refusing to overwrite existing output: {output}")
        report = {"schema_version": 2, "status": "completed_offline_fit", "source_identity": source,
                  "selected_alpha": best_model.alpha, "validation_candidates": candidates,
                  "test": test_metrics, "inference_options": options, "split_manifest": manifest,
                  "admission_sha256": _sha(gate_path), "admission_path": str(gate_path), "manifest_sha256": _sha(manifest_path),
                  "episode_sources": [{"path": str(path.relative_to(ROOT)), "sha256": _sha(path),
                                       "episode_id": ep.episode_id, "scenario_id": ep.scenario_id}
                                      for path, ep in zip(files, episodes)],
                  "training_rows": len(features), "standardization": "train_only_population_std_constants_scale_1",
                  "test_evaluations": 1, "note": "offline metrics are not closed-loop performance"}
        output.mkdir(parents=True, exist_ok=False)
        best_model.save(output / "model.npz")
        with (output / "result.json").open("x") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print(json.dumps({"output": str(output), "selected_alpha": best_model.alpha, "test": test_metrics}, allow_nan=False))
        status = "completed"
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"wind-readout: {error}", file=sys.stderr)
        return 2
    finally:
        if budget is not None:
            budget.finish(status)


if __name__ == "__main__":
    raise SystemExit(main())
