#!/usr/bin/env python3
"""Discriminate the failed first leg from the continuous-task adapter, without tuning."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
from sailboat_routing.runtime import FrozenController, OriginalSegment, SeniorModules
from sailboat_routing.frames import LocalFrame
from sailboat_routing.experiments import Budget, output_directory
import json
import time
import numpy as np


def main():
    out = output_directory("stage_b_failure_diagnostic")
    budget = Budget("stage_b_original_seed11_w180_diagnostic")
    modules = SeniorModules()
    env = OriginalSegment(modules, noise_enabled=False)
    policy = FrozenController(modules, ROOT / "checkpoints/actor.pth", ROOT / "checkpoints/normalizer.pth")
    obs = env.reset(11, 180); policy.reset(obs)
    frame = LocalFrame.for_leg((0, 0), (500, 0))
    prior = json.loads((ROOT / "runs/stage_b/straight_w180.json").read_text())
    trace = []
    first_action_difference = None
    max_state_difference = 0.0
    max_progress_reencoding_error = 0.0
    status = "failed"
    try:
        for step in range(1000):
            budget.check()
            before = env.raw.copy()
            decision = policy.act(obs)
            obs, reward, term, trunc, info = env.step(decision.action)
            encoded = frame.encode(env.raw, before)
            max_progress_reencoding_error = max(max_progress_reencoding_error,
                float(np.max(np.abs(encoded[10:12]-env.raw[10:12]))))
            b = prior["trajectory"][step]
            delta = float(np.max(np.abs(decision.action-np.asarray(b["command"]))))
            if delta > 0 and first_action_difference is None:
                first_action_difference = {"decision_index": step, "max_action_difference": delta}
            max_state_difference = max(max_state_difference,
                float(np.max(np.abs(env.raw-np.asarray(b["raw"])))))
            trace.append({"time": info["time"], "raw": env.raw.tolist(), "command": decision.action.tolist(),
                          "terminated": term, "truncated": trunc})
            if term or trunc: break
        result = {"seed": 11, "wind_degrees": 180, "original_protocol": "same frozen 14D original-scale no-extra-noise path as A",
            "original_success": bool(term and not trunc), "original_steps": step+1,
            "original_distance_to_target_m": float(np.linalg.norm(env.raw[:2]-env.raw[12:14])),
            "original_terminated": term, "original_truncated": trunc,
            "continuous_first_leg_success": False,
            "first_action_difference": first_action_difference,
            "maximum_raw_difference_over_overlap": max_state_difference,
            "maximum_identity_frame_progress_difference": max_progress_reencoding_error,
            "limits": "One discriminating original-entry comparison; no threshold relaxation, controller change or downstream performance experiment"}
        (out / "result.json").write_text(json.dumps(result, indent=2))
        (out / "trajectory.json").write_text(json.dumps(trace))
        print(json.dumps(result, indent=2), flush=True)
        status = "completed"
    finally:
        policy.close(); env.close(); budget.finish(status)


if __name__ == "__main__":
    main()
