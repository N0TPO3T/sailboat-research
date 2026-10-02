"""Real closed-loop supervision with one Actor decision per physical control step.

Wind truth stays here, in the environment, labels and offline metrics. A target
selected from features at t takes effect at the t+1 boundary for EVERY method.
"""
from dataclasses import asdict
import json
import math
from pathlib import Path
import time
from types import MethodType
import numpy as np

from .runtime import ROOT, SeniorModules, FrozenController
from .continuous import ContinuousPhysics
from .frames import LocalFrame, reencode_controller
from .planner import (CircleObstacle, StaticMap, PlannerConfig, PlannerInput,
                      LocalWaypointPlanner, LocalWindEstimate, NoRouteError, NoLocalTargetError)
from .wind_fields import SyntheticWindField
from .wind_readout import CausalWindFilter
from .oracle_local import CurrentLocalWindOracle
from .metrics import segment_circle_clearance, posthoc_tack_events


def build_stack(protocol, limit, radius):
    if protocol["controller_kind"] != "chapter4_14d":
        raise ValueError("This navigation adapter requires the approved fourth-chapter 14D protocol")
    modules = SeniorModules()
    policy = FrozenController(modules, ROOT / protocol["actor"], ROOT / protocol["normalizer"])
    physics = ContinuousPhysics(modules, total_time_limit=limit, world_radius_limit=radius)
    return modules, policy, physics, LocalFrame


def chart_for(scene, suite):
    circles = tuple(CircleObstacle(tuple(row["center_xy"]), row["entity_radius"], row["safety_buffer"])
                    for row in suite["maps"][scene["map"]])
    return StaticMap(tuple(suite["world_bounds"]), circles, grid_resolution=25.0)


def bind_time_indexed_wind(physics, field):
    """Environment-only binding; no field/query object reaches the planner."""
    def update(env):
        g = physics.modules.globals
        speed, direction = field.sample(env.state[:2], float(g.current_time))
        g.w_change_v = g.w_last_v = float(speed)
        g.w_change_d = g.w_last_d = float(direction)
    physics.env.update_wind = MethodType(update, physics.env)
    physics.env.update_wind()


def _write_json(path, value):
    def clean(x):
        if isinstance(x, np.generic): return clean(x.item())
        if isinstance(x, np.ndarray): return clean(x.tolist())
        if isinstance(x, float) and not math.isfinite(x): return None
        if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
        if isinstance(x, (tuple, list)): return [clean(v) for v in x]
        return x
    Path(path).write_text(json.dumps(clean(value), indent=2, allow_nan=False))


def run_episode(scene, suite, admission, out, budget, *, method="geometry_only",
                model=None, capture=False, record_features=True, max_steps=None):
    if method == "estimated_local" and model is None:
        raise ValueError("estimated_local requires a fitted matching readout, never an oracle fallback")
    if model is not None and model.source_identity != admission["source_identity"]:
        raise ValueError("Readout and frozen navigation protocol differ")
    if (capture or model is not None) and not record_features:
        raise ValueError("Capture/readout needs same-forward features")
    if max_steps is not None and (type(max_steps) is not int or max_steps <= 0):
        raise ValueError("max_steps must be a positive integer")
    if capture and max_steps is not None and max_steps < suite["task_time_limit_s"]:
        raise ValueError("Partial interface runs cannot produce complete episode captures")
    out = Path(out).resolve(strict=True)
    if not out.is_relative_to((ROOT / "runs").resolve()):
        raise ValueError("Episode output must remain inside NEW_ROOT/runs")
    trace_file = out / f"{scene['id']}__{method}.json"
    if trace_file.exists(): raise FileExistsError(trace_file)
    started = time.monotonic()
    limit = suite["task_time_limit_s"]
    modules, policy, physics, frame_type = build_stack(admission["protocol"], limit, suite["world_radius_limit_m"])
    chart = chart_for(scene, suite)
    final = tuple(scene["goal"])
    planner = LocalWaypointPlanner(chart, PlannerConfig(**suite["planner_config"]), method)
    field = SyntheticWindField(scene["seed"] + 100000, math.radians(scene["base_direction_degrees"]),
                               scene["profile"], horizon=limit + 1)
    estimate_filter = (CausalWindFilter(model, warmup=suite["readout_warmup"],
                       ema_weight=suite["readout_ema_weight"]) if model is not None else None)
    oracle = CurrentLocalWindOracle(physics)
    raw = physics.reset(scene["seed"], scene["base_direction_degrees"])
    bind_time_indexed_wind(physics, field)
    try:
        route = chart.route(tuple(raw[:2]), final)
        initial = PlannerInput(tuple(raw[:2]), float(raw[3]), None, route, 0.0, None)
        target = planner.plan(initial).target_xy
    except (NoRouteError, NoLocalTargetError) as error:
        clearance = segment_circle_clearance(raw[:2], raw[:2], chart.obstacles)
        row = {"scene_id": scene["id"], "method": method, "complete": True,
            "obstacle_count": len(chart.obstacles), "success": False, "navigation_success": False,
            "reason": type(error).__name__, "time_s": 0.0, "steps": 0, "path_length_m": 0.0,
            "min_entity_clearance_m": clearance["entity_m"], "min_safety_clearance_m": clearance["safety_m"],
            "actuator_variation_rad": 0.0, "sail_variation_rad": 0.0, "rudder_variation_rad": 0.0,
            "target_changes": 0, "tack_count": 0, "wind_side_change_count": 0,
            "planning_seconds": time.monotonic()-started, "reencoding_seconds": 0.0,
            "wall_seconds": time.monotonic()-started, "readout_valid_fraction": None,
            "source_identity": admission["source_identity"], "evidence": str(trace_file.relative_to(ROOT))}
        _write_json(trace_file, {"scene": scene, "row": row, "trajectory": [{"time": 0.0,
            "raw": raw.tolist(), "wind_direction_world": float(modules.globals.w_change_d)}],
            "target_changes": [], "planner_decisions": [], "error": str(error)})
        policy.close(); physics.close()
        print(json.dumps(row), flush=True)
        return row
    physics.set_goal(target)
    raw = physics.raw.copy()
    frame = frame_type.for_leg(raw[:2], target)
    observation = frame.encode(raw, None); policy.reset(observation)
    history, commands = [raw.copy()], []
    trace = [{"time": 0.0, "raw": raw.tolist(), "wind_direction_world": float(modules.globals.w_change_d)}]
    changes, decisions, features, labels, times, frames, counts, switches, wind_changes = [], [], [], [], [], [], [], [], []
    switched = False; reached_final = False; complete = True
    reason = "time_limit"; length = 0.0; variations = np.zeros(2)
    initial_clearance = segment_circle_clearance(raw[:2], raw[:2], chart.obstacles)
    minimum_entity, minimum_safety = initial_clearance["entity_m"], initial_clearance["safety_m"]
    planning_seconds = reencoding_seconds = 0.0
    prediction_valid = 0
    try:
        for _ in range(limit if max_steps is None else min(max_steps, limit)):
            budget.check()
            decision_time = float(modules.globals.current_time)
            # Environment current wind is a PRE-ACTION offline label/diagnostic only.
            current_truth = float(modules.globals.w_change_d)
            decision = policy.act(observation, record_features=record_features)
            estimate = (estimate_filter.update(decision.features, frame_angle=frame.angle,
                        history_count=decision.history_steps) if estimate_filter is not None else None)
            if estimate is not None: prediction_valid += int(estimate.valid)
            wind_input = None
            if method == "oracle_local":
                wind_input = oracle.sample_current()
            elif method == "estimated_local":
                wind_input = LocalWindEstimate(estimate.world_rad, estimate.valid)
            # No raw/info/env/field/seed reaches this explicit whitelist.
            visible = PlannerInput(tuple(raw[:2]), float(raw[3]), target, route, decision_time, wind_input)
            if capture:
                features.append(decision.features.copy())
                labels.append(frame.wind_to_local(current_truth)); times.append(decision_time)
                frames.append(frame.angle); counts.append(decision.history_steps); switches.append(switched)
                wind_changes.append(any(abs(decision_time-t) < 0.5 for t in field.change_onsets))
            switched = False
            plan_started = time.monotonic()
            try:
                plan = planner.plan(visible)
            except (NoRouteError, NoLocalTargetError) as error:
                reason = type(error).__name__; break
            planning_seconds += time.monotonic() - plan_started
            if not decisions or plan.target_xy != target or decision_time % 30 == 0:
                decisions.append({"decision_time": decision_time, "applies_after_time": decision_time+1,
                    "input": asdict(visible), "decision": asdict(plan)})
            before = raw.copy()
            raw, reward, reached_local, truncated, info = physics.step(decision.action)
            raw = raw.copy(); history.append(raw.copy()); commands.append(decision.action.copy())
            length += float(np.linalg.norm(raw[:2]-before[:2]))
            variations += np.abs(raw[8:10].astype(float)-before[8:10])
            clearance = segment_circle_clearance(before[:2], raw[:2], chart.obstacles)
            minimum_entity = min(minimum_entity, clearance["entity_m"])
            minimum_safety = min(minimum_safety, clearance["safety_m"])
            trace.append({"time": float(info["time"]), "raw": raw.tolist(), "command": decision.action.tolist(),
                "physical_action": np.asarray(info["physical_action"]).tolist(), "target": list(target),
                "wind_direction_world": float(modules.globals.w_change_d),
                "wind_used_for_previous_action": current_truth, "safety_clearance_m": clearance["safety_m"]})
            if info["integration_failed"]:
                reason = "integration_failed"; break
            if minimum_entity <= 0:
                reason = "entity_collision"; break
            if np.linalg.norm(raw[:2]-final) <= suite["goal_radius_m"]:
                reached_final = True; reason = "arrived" if minimum_safety > 0 else "arrived_with_buffer_violation"; break
            if truncated:
                reason = "task_limit"; break
            new_target = plan.target_xy
            if np.linalg.norm(np.asarray(new_target)-target) > 1e-6:
                continuity_before = physics.continuity_snapshot()
                physics.set_goal(new_target)
                frame = frame_type.for_leg(raw[:2], new_target)
                observation, elapsed = reencode_controller(policy, frame, history, commands)
                reencoding_seconds += elapsed
                continuity_after = physics.continuity_snapshot()
                if continuity_before != continuity_after:
                    raise AssertionError("Changing a target modified physical/time/wind/RNG state")
                changes.append({"selected_at": decision_time, "applied_at": float(info["time"]),
                    "target": list(new_target), "distance_at_application_m": float(np.linalg.norm(raw[:2]-new_target)),
                    "reencoded_decisions": len(commands), "wall_seconds": elapsed,
                    "continuity_unchanged": True})
                target = new_target; switched = True
            else:
                observation = frame.encode(raw, before)
        else:
            if max_steps is not None and max_steps < limit:
                complete = False; reason = "bounded_interface_smoke"
    except TimeoutError:
        complete = False; reason = "compute_budget_exhausted"
    finally:
        policy.close(); physics.close()
    tack_result = posthoc_tack_events([r["time"] for r in trace], [r["raw"][3] for r in trace],
                                     [r["wind_direction_world"] for r in trace])
    row = {"scene_id": scene["id"], "method": method, "complete": complete, "obstacle_count": len(chart.obstacles),
        "success": bool(reached_final and minimum_safety > 0), "navigation_success": reached_final,
        "reason": reason, "time_s": float(modules.globals.current_time), "steps": len(commands),
        "path_length_m": length, "min_entity_clearance_m": minimum_entity,
        "min_safety_clearance_m": minimum_safety, "actuator_variation_rad": float(variations.sum()),
        "sail_variation_rad": float(variations[0]), "rudder_variation_rad": float(variations[1]),
        "target_changes": len(changes), "tack_count": tack_result["tack_count"],
        "wind_side_change_count": tack_result["wind_side_change_count"],
        "planning_seconds": planning_seconds, "reencoding_seconds": reencoding_seconds,
        "wall_seconds": time.monotonic()-started,
        "readout_valid_fraction": prediction_valid/len(commands) if model is not None and commands else None,
        "source_identity": admission["source_identity"], "evidence": str(trace_file.relative_to(ROOT))}
    _write_json(trace_file, {"scene": scene, "row": row, "trajectory": trace,
        "target_changes": changes, "planner_decisions": decisions, "tack_detection": tack_result,
        "environment_private_wind": field.diagnostics(), "physics_adaptation": physics.adaptation,
        "information_boundary": "Wind truth appears only in this offline evidence; planner inputs are serialized separately"})
    if capture and complete:
        metadata = {"schema_version": 2, "episode_id": scene["id"], "scenario_id": scene["id"],
            "source_identity": admission["source_identity"], "feature_timing": "decision_pre_action"}
        destination = out / (scene["id"]+".npz")
        with destination.open("xb") as stream:
            np.savez_compressed(stream, metadata_json=np.array(json.dumps(metadata)),
                features=np.asarray(features), labels_local_rad=np.asarray(labels),
                decision_time=np.asarray(times), labels_time=np.asarray(times), observed_through_time=np.asarray(times),
                frame_angle=np.asarray(frames), history_count=np.asarray(counts, dtype=np.int64),
                goal_switch=np.asarray(switches, dtype=bool), wind_change=np.asarray(wind_changes, dtype=bool))
        row["dataset"] = str(destination.relative_to(ROOT))
    if reason == "compute_budget_exhausted":
        raise TimeoutError(f"Experiment budget reached; partial real trace saved: {trace_file}")
    print(json.dumps({k:v for k,v in row.items() if k not in ("source_identity",)}, default=float), flush=True)
    return row
