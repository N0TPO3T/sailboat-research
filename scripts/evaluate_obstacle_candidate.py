#!/usr/bin/env python3
"""Bounded candidate A validation, no training or official 300-episode batch."""
from __future__ import annotations
import argparse
import json
import signal
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sailboat_routing.obstacle_candidate import (
    ROOT, MODES, CandidateModules, ObstacleController, ObstacleSegment,
    loading_paths, protocol_manifest)
from sailboat_routing.experiments import Budget
import numpy as np
import torch


def reference_action(controller, current):
    agent = controller.reference()
    action = controller.modules.original.SAC_lstm_countinuous.select_action(
        agent, controller.previous, controller.previous_action, current,
        deterministic=True, total_steps=None, env_id="v0")
    controller.previous = current.copy()
    controller.previous_action = action.copy()
    controller.steps += 1
    return action


def paired_action(ref, candidate, current_ref, current_candidate):
    rng = torch.get_rng_state()
    a = reference_action(ref, current_ref)
    torch.set_rng_state(rng)
    b = candidate.act(current_candidate, record_features=True).action
    errors = {"action": float(np.max(np.abs(a-b)))}
    for name, value in ref.history().items():
        errors[name] = float(np.max(np.abs(value-candidate.history()[name])))
    return a, b, errors


def parity(args, deadline, directory):
    ref, candidate = [ObstacleController(mode=args.mode) for _ in range(2)]
    rng = np.random.RandomState(args.seed)
    initial = rng.normal(size=18).astype(np.float32)
    initial[12:14] = [500, 0]
    ref.reset(initial); candidate.reset(initial)
    rows = []
    try:
        for step in range(16):
            if time.monotonic() >= deadline:
                raise TimeoutError("total wall budget")
            current = initial.copy() if step == 0 else rng.normal(size=18).astype(np.float32)
            current[12:14] = [500, 0]
            _, _, errors = paired_action(ref, candidate, current, current)
            rows.append({"step": step, **errors})
            (directory/"parity_partial.json").write_text(json.dumps({"fixed_input":rows,"closed_loop":[]},indent=2,allow_nan=False))
        fixed_pass = all(all(v <= args.action_tolerance for k,v in row.items() if k != "step") for row in rows)
    finally:
        ref.close(); candidate.close()
    # Independent globals, Dryden state and RNG for each untouched physical class.
    segments = [ObstacleSegment(noise_enabled=args.noise) for _ in range(2)]
    controllers = [ObstacleController(s.modules, mode=args.mode) for s in segments]
    closed = []
    try:
        obs = [s.reset(args.seed, 90, [(190, 10)]) for s in segments]
        for c,o in zip(controllers,obs): c.reset(o)
        for step in range(min(args.max_steps, 32)):
            a,b,errors = paired_action(*controllers, *obs)
            # Reference executes the source evaluator's noise/scaling/step order,
            # independently of the adapter's step implementation.
            reference_segment = segments[0]
            high = reference_segment.env.action_space.high.astype(float)
            physical = reference_segment.modules.network.Action_adapter(
                reference_segment.noise.add_action_noise(a, high), high)
            with reference_segment._rng():
                raw, reward, term, trunc, raw_info = reference_segment.env.step(physical)
            reference_segment.raw = np.asarray(raw, dtype=np.float32).copy()
            left = (reference_segment.noise.add_observation_noise(raw).copy(), float(reward),
                    bool(term), bool(trunc), {"raw": raw.copy(), "physical_action": physical.copy()})
            right = segments[1].step(b)
            if not np.allclose(left[4]["physical_action"], right[4]["physical_action"], rtol=0, atol=args.action_tolerance):
                raise AssertionError("physical action unit/noise pipeline mismatch")
            if not np.isclose(left[1], right[1], rtol=0, atol=args.state_tolerance):
                raise AssertionError("reward mismatch")
            error = float(np.max(np.abs(left[4]["raw"]-right[4]["raw"])))
            closed.append({"step":step, **errors, "state":error,
                "reference_raw":left[4]["raw"].tolist(), "candidate_raw":right[4]["raw"].tolist()})
            (directory/"parity_partial.json").write_text(json.dumps({"fixed_input":rows,"closed_loop":closed},indent=2,allow_nan=False))
            obs = [left[0],right[0]]
            if left[2:4] != right[2:4]:
                raise AssertionError("termination mismatch")
            if left[2] or left[3]: break
        closed_pass = all(row["state"] <= args.state_tolerance and all(row[k] <= args.action_tolerance for k in ("action","h","c","attention_history")) for row in closed)
        return {"fixed_input":rows,"closed_loop":closed,"fixed_pass":fixed_pass,"closed_pass":closed_pass}
    finally:
        for c in controllers: c.close()
        for s in segments: s.close()


def clearance(position, previous, obstacles):
    if not obstacles: return None
    p = np.asarray(position); prev = np.asarray(previous); d=p-prev
    denom = float(d@d)
    return min(float(np.linalg.norm(np.asarray(o)-(prev + (np.clip((np.asarray(o)-prev)@d/denom,0,1) if denom else 0)*d))) - 40. for o in obstacles)


def episode(args, directory, index, wind, obstacles, deadline):
    torch.manual_seed(args.seed)  # Independent reproducible diagnostic episode, not an unseeded legacy batch.
    started = time.monotonic()
    segment = ObstacleSegment(noise_enabled=args.noise)
    controller = ObstacleController(segment.modules, mode=args.mode)
    result = {"index":index,"seed":args.seed,"wind_degrees":wind,"obstacles":obstacles,
        "mode":args.mode,"noise":args.noise,"success":False,"steps":0,"reason":"step_limit",
        "minimum_safety_margin_m":None,"anomaly":None}
    trajectory = directory / f"trajectory_{index:02d}.jsonl"
    try:
        obs = segment.reset(args.seed, wind, obstacles)
        controller.reset(obs)
        previous = segment.raw[:2].copy()
        minimum = clearance(previous, previous, obstacles)
        result["minimum_safety_margin_m"] = minimum
        with trajectory.open("x") as out:
            out.write(json.dumps({"step":0,"raw":segment.raw.tolist()})+"\n"); out.flush()
            for step in range(args.max_steps):
                if time.monotonic() >= deadline:
                    raise TimeoutError("total wall budget")
                action = controller.act(obs).action
                obs, reward, terminated, truncated, info = segment.step(action)
                margin = clearance(info["raw"][:2], previous, obstacles)
                if margin is not None: minimum = min(minimum, margin)
                previous = info["raw"][:2].copy()
                result["steps"] = step+1
                result["minimum_safety_margin_m"] = minimum
                out.write(json.dumps({"step":step+1,"raw":info["raw"].tolist(),"action":action.tolist(),
                    "physical_action":info["physical_action"].tolist(),"reward":reward,"time":info["time"],"safety_margin_m":margin})+"\n")
                out.flush()
                if terminated or truncated:
                    result["success"] = bool(terminated and not truncated)
                    result["reason"] = "goal" if result["success"] else "collision" if minimum is not None and minimum < 0 else "environment_truncation"
                    break
    except Exception as exc:
        result["reason"] = "wall_limit" if isinstance(exc, TimeoutError) else "exception"
        result["anomaly"] = f"{type(exc).__name__}: {exc}"
    finally:
        controller.close(); segment.close()
        result["wall_seconds"] = time.monotonic()-started
        result["trajectory"] = str(trajectory)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase",choices=("parity","pilot","capability"),required=True)
    parser.add_argument("--mode",choices=MODES,default="legacy_training")
    parser.add_argument("--seed",type=int,default=0)
    parser.add_argument("--max-steps",type=int,default=1000)
    parser.add_argument("--max-wall-seconds",type=float,default=600.)
    parser.add_argument("--scenarios",type=int,default=8)
    parser.add_argument("--noise",action=argparse.BooleanOptionalAction,default=True)
    parser.add_argument("--action-tolerance",type=float,default=1e-6)
    parser.add_argument("--state-tolerance",type=float,default=1e-5)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    if not 1 <= args.max_steps <= 1000 or not 0 < args.max_wall_seconds <= 600 or not 1 <= args.scenarios <= 8:
        parser.error("bounds: steps 1..1000, wall (0,600], scenarios 1..8")
    if not 0 < args.action_tolerance <= 1e-6 or not 0 < args.state_tolerance <= 1e-5:
        parser.error("tolerances may only tighten declared 1e-6/1e-5")
    directory = (args.output or ROOT / "runs" / ("obstacle_"+args.phase+"_"+str(time.time_ns()))).resolve()
    if not directory.is_relative_to((ROOT/"runs").resolve()):
        parser.error("output must be exclusive under NEW_ROOT/runs")
    directory.mkdir(parents=True, exist_ok=False)
    budget = Budget("obstacle_candidate_"+args.phase+"_"+args.mode)
    budget.check()
    args.max_wall_seconds = min(args.max_wall_seconds, budget.limit-budget.used)
    started = time.monotonic(); deadline = started+args.max_wall_seconds
    torch.manual_seed(args.seed)
    report = {"phase":args.phase,"paths":loading_paths(),"module_paths":CandidateModules().paths,"protocol":protocol_manifest(),
        "mode":args.mode,"noise":args.noise,"tolerances":{"action_h_c_history":args.action_tolerance,"state":args.state_tolerance},"episodes":[]}
    def timeout(signum, frame): raise TimeoutError("total wall budget (including physical integrator)")
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL,args.max_wall_seconds)
    try:
        if args.phase == "parity":
            report["parity"] = parity(args,deadline,directory)
        else:
            scenarios = [(wind, obs) for obs in ([],[(190.,10.)]) for wind in (0,90,150,180)]
            count = 1 if args.phase == "pilot" else args.scenarios
            # First episode is timing pilot; do not launch remaining scenes before it finishes.
            for index,(wind,obstacles) in enumerate(scenarios[:count]):
                if time.monotonic() >= deadline:
                    report["not_started"] = scenarios[index:count]; break
                row = episode(args,directory,index,wind,obstacles,deadline)
                report["episodes"].append(row)
                (directory/"results.json").write_text(json.dumps(report,indent=2,allow_nan=False))
                if row["reason"] == "wall_limit":
                    report["not_started"] = scenarios[index+1:count]; break
            if report["episodes"]:
                report["pilot_seconds"] = report["episodes"][0]["wall_seconds"]
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        report["wall_seconds"] = time.monotonic()-started
        budget.finish("interrupted" if "error" in report or "not_started" in report else "completed")
        (directory/"results.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(directory/"results.json")
    return int("error" in report or (args.phase == "parity" and not all(report.get("parity",{}).get(k,False) for k in ("fixed_pass","closed_pass"))))

if __name__ == "__main__":
    raise SystemExit(main())
