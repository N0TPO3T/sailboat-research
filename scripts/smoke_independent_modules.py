#!/usr/bin/env python3
"""Synthetic mathematical/API checks only; NOT wind-estimation or navigation performance."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
from sailboat_routing.runtime import SeniorModules
from sailboat_routing.continuous import ContinuousPhysics
from sailboat_routing.experiments import Budget, output_directory
from sailboat_routing.wind_readout import RidgeWindReadout, CausalWindFilter, circular_metrics
from sailboat_routing.planner import CircleObstacle, StaticMap, PlannerInput, PlannerConfig, LocalWaypointPlanner, LocalWindEstimate
from sailboat_routing.oracle_local import CurrentLocalWindOracle
from dataclasses import asdict
import json
import math
import subprocess
import numpy as np


def main():
    out = output_directory("independent_module_smoke")
    budget = Budget("synthetic_math_and_information_boundary_smoke")
    status = "failed"
    physics = None
    try:
        # Explicit synthetic basis, never advertised as captured Actor features.
        angles = np.linspace(-math.pi, math.pi, 48, endpoint=False)
        features = np.zeros((48, 270)); features[:, 0] = np.sin(angles); features[:, 1] = np.cos(angles)
        fixture_identity = {"actor_sha256": "0" * 64, "normalizer_sha256": "1" * 64,
                            "feature_schema": "frozen_obs14+lstm_ln256_pre_action_v1"}
        model = RidgeWindReadout.fit(features, angles, alpha=0.1, source_identity=fixture_identity)
        fixture_path = out / "SYNTHETIC_NOT_DEPLOYABLE_model.npz"
        model.save(fixture_path)
        restored = RidgeWindReadout.load(fixture_path, expected_dimension=270, expected_source_identity=fixture_identity)
        state = CausalWindFilter(restored, warmup=10, ema_weight=1.0)
        fixture = np.zeros(270); fixture[:2] = [math.sin(0.4), math.cos(0.4)]
        estimate = state.update(fixture, frame_angle=0.2, history_count=10)
        if not estimate.valid or abs(math.atan2(math.sin(estimate.world_rad-0.6), math.cos(estimate.world_rad-0.6))) > 1e-6:
            raise AssertionError("Synthetic sin/cos fit, restore or frame conversion failed")
        chart = StaticMap((-1000, 2000, -1000, 1000))
        route = chart.route((0.0, 0.0), (1000.0, 0.0))
        input_estimate = LocalWindEstimate(estimate.world_rad, estimate.valid)
        visible = PlannerInput((0.0, 0.0), 0.0, None, route, 0.0, input_estimate)
        formal_before = LocalWaypointPlanner(chart, mode="estimated_local").plan(visible)
        # A real physics object is used for the diagnostic tap, never for formal planner input.
        physics = ContinuousPhysics(SeniorModules())
        physics.reset(71, 0)
        oracle = CurrentLocalWindOracle(physics)
        true_before = oracle.sample_current()
        physics.modules.globals.w_change_d = math.pi
        true_after = oracle.sample_current()
        formal_after = LocalWaypointPlanner(chart, mode="estimated_local").plan(visible)
        if formal_before != formal_after or true_before == true_after:
            raise AssertionError("Hidden true wind leaked into formal planning or local oracle failed")
        decisions = {}
        for mode, wind in (("geometry_only", None), ("oracle_local", true_after), ("estimated_local", input_estimate)):
            decision = LocalWaypointPlanner(chart, mode=mode).plan(
                PlannerInput((0.0, 0.0), 0.0, None, route, 0.0, wind))
            decisions[mode] = asdict(decision)
        obstacle_map = StaticMap((0, 1200, -400, 400), (CircleObstacle((600, 0), 100, 40),), 25)
        obstacle_route = obstacle_map.route((0, 0), (1200, 0))
        if not all(obstacle_map.segment_clear(a, b) for a, b in zip(obstacle_route, obstacle_route[1:])):
            raise AssertionError("A* geometry violated its own map buffer")
        gate = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/fit_wind_readout.py"),
            "--episodes", str(ROOT / "runs/stage_b"), "--manifest", str(ROOT / "configs/stage_b.json")],
            capture_output=True, text=True, timeout=30)
        if gate.returncode != 2:
            raise AssertionError("Real failed Stage B gate did not block the fitting CLI")
        result = {"passed": True, "scope": "Synthetic math and real API/information-boundary smoke only",
            "not_real_wind_accuracy": True, "not_three_method_performance": True,
            "fixture_estimate": asdict(estimate), "fixture_model_identity": fixture_identity,
            "formal_output_unchanged_when_hidden_current_true_wind_changed": True,
            "oracle_current_angles": [true_before.angle_world_rad, true_after.angle_world_rad],
            "planner_api_decisions": decisions, "static_obstacle_route": obstacle_route,
            "production_fit_gate": {"returncode": gate.returncode, "stderr": gate.stderr.strip()},
            "limits": "No real feature collection, no production readout fit, no C/D closed-loop comparison; fixture model must not be deployed"}
        (out / "result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2), flush=True)
        status = "completed"
    finally:
        if physics is not None: physics.close()
        budget.finish(status)


if __name__ == "__main__":
    main()
