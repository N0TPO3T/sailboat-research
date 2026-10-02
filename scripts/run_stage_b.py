#!/usr/bin/env python3
"""Six predeclared 1 km real-dynamics tasks; no low-level training or resets at waypoints."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
from sailboat_routing.runtime import SeniorModules, FrozenController
from sailboat_routing.frames import LocalFrame, reencode_controller
from sailboat_routing.continuous import ContinuousPhysics
from sailboat_routing.experiments import Budget, output_directory
import argparse
import hashlib
import json
import time
import numpy as np


def run_case(scene, config, out, budget):
    started = time.monotonic()
    modules = SeniorModules()
    physics = ContinuousPhysics(modules, total_time_limit=config["total_time_limit_s"],
                                world_radius_limit=config["world_radius_limit_m"])
    policy = FrozenController(modules, ROOT / "checkpoints/actor.pth", ROOT / "checkpoints/normalizer.pth")
    raw = physics.reset(scene["seed"], scene["wind_degrees"])
    goals = [np.asarray(g, dtype=float) for g in scene["goals"]]
    frame = LocalFrame.for_leg(raw[:2], goals[0]); physics.set_goal(goals[0])
    history = [raw.copy()]; commands = []
    observation = frame.encode(raw, None); policy.reset(observation)
    index = 0; segment_started = 0.0; switches = []; trace = []
    reason = "time_limit"; success = False; length = 0.0
    sail_variation = rudder_variation = 0.0
    try:
        for step in range(config["total_time_limit_s"]):
            budget.check()
            if not np.array_equal(observation[12:14], [500, 0]):
                raise AssertionError("Frozen normalizer target contract violated")
            decision = policy.act(observation, record_features=True)
            before = raw.copy()
            raw, reward, reached, truncated, info = physics.step(decision.action)
            raw = raw.copy(); commands.append(decision.action.copy()); history.append(raw.copy())
            length += float(np.linalg.norm(raw[:2]-before[:2]))
            sail_variation += abs(float(raw[8]-before[8])); rudder_variation += abs(float(raw[9]-before[9]))
            trace.append({"time": info["time"], "raw": raw.tolist(), "command": decision.action.tolist(),
                          "goal_index": index, "goal_world": goals[index].tolist(), "frame_angle": float(frame.angle),
                          "physical_action": np.asarray(info["physical_action"]).tolist()})
            if info.get("integration_failed", False):
                reason = "integration_failed"; break
            if truncated:
                reason = "task_limit"; break
            if reached:
                if index == len(goals)-1:
                    success = True; reason = "arrived"; break
                continuous_before = physics.continuity_snapshot()
                index += 1
                physics.set_goal(goals[index])
                frame = LocalFrame.for_leg(raw[:2], goals[index])
                observation, elapsed = reencode_controller(policy, frame, history, commands)
                continuous_after = physics.continuity_snapshot()
                if continuous_before != continuous_after:
                    raise AssertionError("Intermediate target change altered physical/time/wind/RNG state")
                switches.append({"time": info["time"], "new_goal_index": index,
                    "reencoded_decisions": len(commands), "reencoding_wall_seconds": elapsed,
                    "physical_time_wind_rng_unchanged": True,
                    "before": continuous_before, "after": continuous_after})
                segment_started = info["time"]
            else:
                observation = frame.encode(raw, before)
            if info["time"]-segment_started >= config["segment_time_limit_s"]:
                reason = "segment_time_limit"; break
        result = {"scene": scene["id"], "success": success, "reason": reason,
            "steps": step+1, "time_s": float(modules.globals.current_time), "path_length_m": length,
            "final_distance_m": float(np.linalg.norm(raw[:2]-goals[-1])),
            "intermediate_targets_reached": index, "target_switches": switches,
            "sail_variation_rad": sail_variation, "rudder_variation_rad": rudder_variation,
            "wall_seconds": time.monotonic()-started}
        path = out / (scene["id"]+".json")
        path.write_text(json.dumps({"scene": scene, "result": result, "trajectory": trace}, indent=2))
        result["evidence"] = str(path.relative_to(ROOT))
        print(json.dumps({k:v for k,v in result.items() if k!="target_switches"}), flush=True)
        return result
    finally:
        physics.close(); policy.close()


def plot(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for row, ax in zip(rows, axes.flat):
        record = json.loads((ROOT / row["evidence"]).read_text())
        xy = np.array([[0, 0]]+[r["raw"][:2] for r in record["trajectory"]])
        route = np.array([[0, 0]]+record["scene"]["goals"])
        ax.plot(route[:, 0], route[:, 1], "k--", label="targets")
        ax.plot(xy[:, 0], xy[:, 1], label="real trajectory")
        ax.set_title(row["scene"]+": "+row["reason"]); ax.grid(True)
        ax.set_aspect("equal", adjustable="datalim"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out / "trajectories.png", dpi=140); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default="stage_b")
    args = parser.parse_args()
    gate = json.loads((ROOT / "runs/stage_a/capability/result.json").read_text())
    if not gate["passed"]:
        raise RuntimeError("A capability gate failed; B performance runs are blocked")
    config = json.loads((ROOT / "configs/stage_b.json").read_text())
    out = output_directory(args.run_name)
    (out / "config.json").write_text(json.dumps(config, indent=2))
    budget = Budget("stage_b"); status = "failed"
    try:
        rows = []
        with (out / "episodes.jsonl").open("x") as stream:
            for scene in config["scenarios"]:
                row = run_case(scene, config, out, budget)
                rows.append(row); stream.write(json.dumps(row)+"\n"); stream.flush()
        result = {"passed": sum(r["success"] for r in rows) >= config["gate"]["minimum_successes"],
            "successes": sum(r["success"] for r in rows), "total": len(rows),
            "continuity_checks": sum(len(r["target_switches"]) for r in rows), "episodes": rows,
            "memory_protocol": config["memory"], "limits": "Fixed small development set, unchanged frozen Actor and original real dynamics"}
        (out / "result.json").write_text(json.dumps(result, indent=2)); plot(rows, out)
        print(json.dumps({k:v for k,v in result.items() if k!="episodes"}, indent=2), flush=True)
        status = "completed"
    except Exception as error:
        (out / "error.json").write_text(json.dumps({"type": type(error).__name__, "message": str(error)}, indent=2))
        raise
    finally:
        budget.finish(status)


if __name__ == "__main__":
    main()
