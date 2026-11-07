#!/usr/bin/env python3
"""Bounded migration parity and original-scale navigation; never trains a policy."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
from sailboat_routing.runtime import FrozenController, OriginalSegment, SeniorModules
import argparse
import ast
import hashlib
import importlib.metadata
import json
import random
import time
from types import MethodType, SimpleNamespace
import numpy as np
import torch

CONFIG = json.loads((ROOT / "configs/stage_a.json").read_text())
START = time.monotonic()
LEDGER = ROOT / "runs/computation.jsonl"
USED = sum(json.loads(line)["wall_seconds"] for line in LEDGER.read_text().splitlines()) if LEDGER.exists() else 0.0


def check_budget():
    if USED + time.monotonic() - START >= CONFIG["compute"]["total_experiment_wall_seconds_budget"]:
        raise TimeoutError("Initial cumulative experiment budget exhausted; no further episodes launched")


def controller(modules):
    return FrozenController(modules, ROOT / CONFIG["actor"], ROOT / CONFIG["normalizer"])


def reference_policy(modules):
    """Execute the untouched original select_action method, without creating a learner."""
    path = ROOT / "runs/audit/reference/SAC_lstm.py"
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SAC_lstm_countinuous")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "select_action")
    namespace = {"torch": torch, "np": np}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
    actor = modules.network.Actor(14, 2, (256, 256))
    actor.load_state_dict(torch.load(ROOT / CONFIG["actor"], map_location="cpu", weights_only=True), strict=True)
    actor.eval().requires_grad_(False)
    normalizer = modules.network.ZScoreNormalizer(14, torch.device("cpu"))
    normalizer.load_state_dict(torch.load(ROOT / CONFIG["normalizer"], map_location="cpu", weights_only=True))
    agent = SimpleNamespace(actor=actor, state_normalizer=normalizer, dvc=torch.device("cpu"))
    agent.select_action = MethodType(namespace["select_action"], agent)
    return agent


def compare(left, right, atol):
    left, right = np.asarray(left), np.asarray(right)
    if not np.allclose(left, right, rtol=CONFIG["parity"]["rtol"], atol=atol):
        raise AssertionError(f"Parity failure; max absolute error={np.max(np.abs(left-right))}")
    return float(np.max(np.abs(left-right)))


def wind_override(modules, degrees):
    g = modules.globals
    angle = float(np.deg2rad(degrees))
    g.w0 = [8.0, angle]
    g.w_ini_v = g.w_last_v = g.w_change_v = 8.0
    g.w_ini_d = g.w_last_d = g.w_change_d = angle


def closed_reference(seed, degrees, noise_enabled):
    modules = SeniorModules(ROOT / "runs/audit/reference")
    agent = reference_policy(modules)
    env = modules.environment.Sailboat_nowind_last(render_mode=None)
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    observation, _ = env.reset(seed=seed)
    wind_override(modules, degrees)
    noise = modules.noise.NoiseManager(sensor_noise_ratio=0.03, actuator_noise_ratio=0.03,
        enable_sensor_noise=noise_enabled, enable_actuator_noise=noise_enabled, seed=seed)
    current = noise.add_observation_noise(observation).copy()
    previous = current.copy(); previous_action = np.zeros(2, dtype=np.float32)
    rows = []
    try:
        for _ in range(CONFIG["parity"]["closed_loop_steps"]):
            action = agent.select_action(previous, previous_action, current, True, 0, env_id="reference")
            high = env.action_space.high.astype(float)
            physical = modules.network.Action_adapter(noise.add_action_noise(action, high), high)
            raw, reward, term, trunc, _ = env.step(physical)
            h, c = agent.actor.hidden_states["reference"]
            rows.append(dict(action=action.copy(), physical=np.asarray(physical).copy(), raw=raw.copy(),
                reward=reward, h=h.detach().numpy().copy(), c=c.detach().numpy().copy(),
                time=modules.globals.current_time, terminated=term, truncated=trunc))
            previous, previous_action = current.copy(), action.copy()
            current = noise.add_observation_noise(raw).copy()
            if term or trunc: break
    finally:
        env.close()
    return rows


def parity(out):
    modules = SeniorModules()
    reference = reference_policy(SeniorModules(ROOT / "runs/audit/reference"))
    migrated = controller(modules)
    recorder = controller(SeniorModules())
    rng = np.random.RandomState(810)
    observations = rng.normal(size=(CONFIG["parity"]["fixed_inputs"], 14)).astype(np.float32)
    observations[:, 12:14] = [500.0, 0.0]
    previous = observations[0].copy(); previous_action = np.zeros(2, dtype=np.float32)
    migrated.reset(previous); recorder.reset(previous)
    maximum = {"action": 0.0, "hidden": 0.0, "feature_sidepath_action": 0.0}
    for observation in observations:
        expected = reference.select_action(previous, previous_action, observation, True, 0, env_id="reference")
        actual = migrated.act(observation)
        recorded = recorder.act(observation, record_features=True)
        maximum["action"] = max(maximum["action"], compare(expected, actual.action, CONFIG["parity"]["atol_action_hidden"]))
        maximum["feature_sidepath_action"] = max(maximum["feature_sidepath_action"], compare(actual.action, recorded.action, 0.0))
        for expected_hidden, actual_hidden in zip(reference.actor.hidden_states["reference"], migrated.hidden()):
            maximum["hidden"] = max(maximum["hidden"], compare(expected_hidden.detach().numpy(), actual_hidden, CONFIG["parity"]["atol_action_hidden"]))
        if recorded.features.shape != (270,) or not np.isfinite(recorded.features).all():
            raise AssertionError("Invalid same-forward causal feature capture")
        previous, previous_action = observation.copy(), expected.copy()
    migrated.close(); recorder.close()
    closed = []
    for noisy in (False, True):
        expected_rows = closed_reference(123, 90.0, noisy)
        m = SeniorModules(); policy = controller(m); env = OriginalSegment(m, noise_enabled=noisy)
        observation = env.reset(123, 90.0); policy.reset(observation)
        errors = {"action": 0.0, "physical": 0.0, "raw": 0.0, "reward": 0.0, "hidden": 0.0}
        try:
            for expected in expected_rows:
                actual = policy.act(observation, record_features=True)
                observation, reward, term, trunc, info = env.step(actual.action)
                for name, value in (("action", actual.action), ("physical", info["physical_action"]), ("raw", info["raw"]), ("reward", reward)):
                    errors[name] = max(errors[name], compare(expected[name], value, CONFIG["parity"]["atol_state_reward"]))
                for key, hidden in zip(("h", "c"), policy.hidden()):
                    errors["hidden"] = max(errors["hidden"], compare(expected[key], hidden, CONFIG["parity"]["atol_action_hidden"]))
                assert (term, trunc, info["time"]) == (expected["terminated"], expected["truncated"], expected["time"])
        finally:
            env.close(); policy.close()
        closed.append({"noise_enabled": noisy, "steps": len(expected_rows), "maximum_absolute_errors": errors})
    normalizer = torch.load(ROOT / CONFIG["normalizer"], map_location="cpu", weights_only=True)
    return {"passed": True, "fixed_inputs": len(observations), "maximum_absolute_errors": maximum,
        "closed_loop": closed, "normalizer": {"count": int(normalizer["count"]), "mean": normalizer["mean"].tolist(), "var": normalizer["var"].tolist()},
        "runtime_module_paths": modules.paths, "versions": {p: importlib.metadata.version(p) for p in ("torch", "numpy", "scipy", "gymnasium", "pygame")},
        "limits": "Migration parity only; no navigation capability claim"}


def episode(seed, wind, out, *, pilot=False):
    check_budget()
    modules = SeniorModules(); policy = controller(modules)
    env = OriginalSegment(modules, noise_enabled=CONFIG["noise_enabled"])
    start = time.monotonic()
    observation = env.reset(seed, wind); policy.reset(observation)
    trajectory = [{"time": 0, "raw": env.raw.tolist()}]
    reward_sum = 0.0; length = 0.0; sail_variation = 0.0; rudder_variation = 0.0
    reason = "time_limit"; success = False
    try:
        for step in range(CONFIG["episode_limit"]):
            check_budget()
            if pilot and time.monotonic()-start > CONFIG["compute"]["pilot_wall_seconds_limit"]:
                raise TimeoutError("Pilot exceeded declared wall-time budget")
            before = env.raw.copy()
            action = policy.act(observation)
            observation, reward, term, trunc, info = env.step(action.action)
            raw = info["raw"]
            reward_sum += reward; length += float(np.linalg.norm(raw[:2]-before[:2]))
            sail_variation += abs(float(raw[8]-before[8])); rudder_variation += abs(float(raw[9]-before[9]))
            trajectory.append({"time": info["time"], "raw": raw.tolist(), "command": action.action.tolist(),
                "physical_action": info["physical_action"].tolist(), "reward": reward,
                "wind_direction_for_evaluation_only": float(modules.globals.w_change_d)})
            if term or trunc:
                success = bool(term and not trunc)
                reason = "arrived" if success else ("out_of_bounds" if np.linalg.norm(raw[:2]) >= 750 else "truncated")
                break
        row = {"seed": seed, "wind_degrees": wind, "success": success, "reason": reason,
            "steps": step+1, "navigation_time_s": float(modules.globals.current_time),
            "distance_to_target_m": float(np.linalg.norm(env.raw[:2]-env.raw[12:14])), "length_m": length,
            "reward": reward_sum, "sail_variation_rad": sail_variation, "rudder_variation_rad": rudder_variation,
            "wall_seconds": time.monotonic()-start}
    finally:
        env.close(); policy.close()
    trace_path = out / f"wind{wind}_seed{seed}.json"
    trace_path.write_text(json.dumps({"episode": row, "trajectory": trajectory}, indent=2))
    row["trajectory"] = str(trace_path.relative_to(ROOT))
    print(json.dumps(row), flush=True)
    return row


def plot_rows(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for wind, ax in zip(CONFIG["wind_degrees"], axes.flat):
        for row in rows:
            if row["wind_degrees"] != wind: continue
            trace = json.loads((ROOT / row["trajectory"]).read_text())["trajectory"]
            xy = np.array([r["raw"][:2] for r in trace])
            ax.plot(xy[:, 0], xy[:, 1], label=f"seed={row['seed']} {row['reason']}")
        ax.scatter([0, 500], [0, 0], marker="x", color="black")
        ax.set_title(f"Native Dryden mean direction {wind} deg")
        ax.set_aspect("equal", adjustable="datalim"); ax.legend(fontsize=7); ax.grid(True)
        ax.set_xlabel("world x / m"); ax.set_ylabel("world y / m")
    fig.tight_layout(); fig.savefig(out / "trajectories.png", dpi=140); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("parity", "pilot", "capability"))
    parser.add_argument("--run-name", default="stage_a", help="New single-directory name under runs; existing results are never overwritten")
    args = parser.parse_args()
    if Path(args.run_name).name != args.run_name or args.run_name in (".", ".."):
        parser.error("run-name must be one directory name")
    out = ROOT / "runs" / args.run_name / args.mode
    out.mkdir(parents=True, exist_ok=False)
    (out / "config.json").write_text(json.dumps(CONFIG, indent=2))
    status = "failed"
    try:
        if args.mode == "parity":
            result = parity(out)
        else:
            proof = json.loads((ROOT / "runs" / args.run_name / "parity/result.json").read_text())
            if not proof["passed"]: raise RuntimeError("Migration parity gate failed")
            if args.mode == "pilot":
                rows = [episode(CONFIG["seeds"][0], CONFIG["wind_degrees"][0], out, pilot=True)]
                result = {"episodes": rows, "limits": "One pilot episode; capability gate not yet assessed"}
            else:
                pilot = json.loads((ROOT / "runs" / args.run_name / "pilot/result.json").read_text())
                rows = list(pilot["episodes"])
                if rows[0]["wall_seconds"] > CONFIG["compute"]["pilot_wall_seconds_limit"]:
                    raise RuntimeError("Pilot too slow; do not launch batch")
                with (out / "episodes.jsonl").open("x") as stream:
                    stream.write(json.dumps(rows[0])+"\n"); stream.flush()
                    for wind in CONFIG["wind_degrees"]:
                        for seed in CONFIG["seeds"]:
                            if (wind, seed) == (rows[0]["wind_degrees"], rows[0]["seed"]): continue
                            row = episode(seed, wind, out)
                            rows.append(row); stream.write(json.dumps(row)+"\n"); stream.flush()
                per_wind = {str(w): sum(r["success"] for r in rows if r["wind_degrees"] == w) for w in CONFIG["wind_degrees"]}
                passed = (sum(r["success"] for r in rows) >= CONFIG["capability_gate"]["minimum_successes"]
                    and min(per_wind.values()) >= CONFIG["capability_gate"]["minimum_successes_per_wind"])
                result = {"passed": passed, "episodes": rows, "successes": sum(r["success"] for r in rows),
                    "total": len(rows), "successes_per_wind": per_wind,
                    "next_stage": "B" if passed else "BLOCKED: do not run B/C/D performance experiments or retrain low-level",
                    "limits": "Fixed small development set; not a reproduction of paper success rates"}
                plot_rows(rows, out)
        (out / "result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps({k:v for k,v in result.items() if k != "episodes"}, indent=2), flush=True)
        status = "completed"
    except Exception as error:
        (out / "error.json").write_text(json.dumps({"type": type(error).__name__, "message": str(error)}, indent=2))
        raise
    finally:
        with LEDGER.open("a") as stream:
            stream.write(json.dumps({"command": args.mode, "wall_seconds": time.monotonic()-START, "status": status})+"\n")


if __name__ == "__main__":
    main()
