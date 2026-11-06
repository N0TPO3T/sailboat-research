"""Continuous world-coordinate navigation over the unmodified senior dynamics."""
from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import pickle
import random
import textwrap
from types import MethodType
from pathlib import Path

import numpy as np

from .runtime import OriginalSegment


class UpstreamStepMismatch(RuntimeError):
    """The inherited step no longer has the audited termination structure."""


def _tree(source):
    return ast.parse(textwrap.dedent(source))


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _adapt_step(environment):
    original = environment.Sailboat_nowind_last.step
    filename = inspect.getsourcefile(original)
    snapshot_sha256 = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    if snapshot_sha256 != "8668f769194b65857667b255eeca6467e45d3e248131ea46af245bfbdc156313":
        raise UpstreamStepMismatch("Inherited environment differs from the audited immutable snapshot")
    source = textwrap.dedent(inspect.getsource(original))
    tree = _tree(source)
    expected_condition = _tree(
        "if integration_failed or dis_to_yuandian >= 750 or globals.current_time >= globals.total_time:\n"
        "    truncated = True\nelse:\n    truncated = False\n"
    ).body[0]
    expected_return = _tree(
        "return globals.state, reward, terminated, truncated, {}"
    ).body[0]
    expected_rollback = _tree(
        "if integration_failed:\n"
        "    globals.current_state[0:8] = previous_state[0:8]\n"
        "    self.state[0:8] = previous_state[0:8]\n"
    ).body[0]
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise UpstreamStepMismatch("Expected exactly one inherited step function")
    function = tree.body[0]
    if function.name != "step" or _dump(function.args) != _dump(_tree("def step(self, action): pass").body[0].args):
        raise UpstreamStepMismatch("Unrecognized step signature")
    matches = [node for node in function.body if _dump(node) == _dump(expected_condition)]
    returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)
               and isinstance(node.value, ast.Tuple) and len(node.value.elts) == 5]
    rollbacks = [node for node in function.body if _dump(node) == _dump(expected_rollback)]
    # Reject new/unrecognized failure handling, rather than guessing from truncated.
    failure_names = [node for node in ast.walk(function)
                     if isinstance(node, ast.Name) and node.id == "integration_failed"]
    assignments = [node for node in ast.walk(function) if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "integration_failed"
                           for target in node.targets)]
    values = [node.value.value for node in assignments if isinstance(node.value, ast.Constant)]
    if (len(matches) != 1 or len(returns) != 1 or returns[0] is not function.body[-1]
            or _dump(returns[0]) != _dump(expected_return) or len(rollbacks) != 1
            or len(failure_names) != 7 or len(assignments) != 5
            or values.count(False) != 1 or values.count(True) != 4
            or any(len(node.targets) != 1 for node in assignments)):
        raise UpstreamStepMismatch("Unrecognized truncation, integration failure, or return structure")
    before = _dump(tree)
    condition = matches[0]
    old_test = condition.test
    condition.test = ast.copy_location(ast.Name(id="integration_failed", ctx=ast.Load()), old_test)
    result = returns[0]
    old_info = result.value.elts[-1]
    result.value.elts[-1] = ast.copy_location(ast.Dict(
        keys=[ast.Constant(value="integration_failed")],
        values=[ast.Name(id="integration_failed", ctx=ast.Load())]), old_info)
    ast.fix_missing_locations(tree)
    after = _dump(tree)
    # Reverse the two allowed edits and compare every remaining AST node before compile.
    restored = copy.deepcopy(tree)
    restored_function = restored.body[0]
    restored_function.body[function.body.index(condition)].test = copy.deepcopy(old_test)
    restored_function.body[-1].value.elts[-1] = copy.deepcopy(old_info)
    if _dump(restored) != before:
        raise UpstreamStepMismatch("Adaptation changed more than the two permitted AST fields")
    filename = inspect.getsourcefile(original)
    namespace = dict(original.__globals__)
    exec(compile(tree, filename + "::continuous-step", "exec"), namespace)
    record = {
        "source": filename,
        "snapshot_sha256": snapshot_sha256,
        "source_step_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "original_ast_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "adapted_ast_sha256": hashlib.sha256(after.encode()).hexdigest(),
        "changes": [
            "step truncation test: integration_failed only; remove 750m and globals.total_time",
            "step return info: add the original integration_failed flag",
        ],
        "unchanged": "All other AST nodes, including ODE, rollback, action quantization, reward and wind update",
    }
    return namespace["step"], record


class ContinuousPhysics:
    """No extra sensor/actuator noise; reaching a goal is not a physical reset.

    Limits are absolute simulation time and world-origin Euclidean radius. The
    inherited reward sees integration failure only; wrapper limits do not alter it.
    Each instance must own its SeniorModules (whose globals are mutable).
    """

    _rng = OriginalSegment._rng

    def __init__(self, modules, total_time_limit=2400, world_radius_limit=5000):
        self.modules = modules
        self.total_time_limit = float(total_time_limit)
        self.world_radius_limit = float(world_radius_limit)
        if (not np.isfinite(self.total_time_limit) or self.total_time_limit <= 0
                or not np.isfinite(self.world_radius_limit) or self.world_radius_limit <= 0):
            raise ValueError("Continuous task limits must be finite and positive")
        step, self.adaptation = _adapt_step(modules.environment)
        self.random_state = random.Random(0).getstate()
        self.numpy_state = np.random.RandomState(0).get_state()
        # Upstream construction invokes reset; isolate that too.
        with self._rng():
            self.env = modules.environment.Sailboat_nowind_last(render_mode=None)
        self.env.step = MethodType(step, self.env)
        self.raw = None

    def reset(self, seed, wind_degrees=None):
        if wind_degrees is not None and not np.isfinite(wind_degrees):
            raise ValueError("Wind direction must be finite degrees")
        self.random_state = random.Random(seed).getstate()
        self.numpy_state = np.random.RandomState(seed).get_state()
        with self._rng():
            raw, _ = self.env.reset(seed=seed)
        if wind_degrees is not None:
            direction = float(np.deg2rad(wind_degrees))
            g = self.modules.globals
            g.w0 = [8.0, direction]
            g.w_ini_v = g.w_last_v = g.w_change_v = 8.0
            g.w_ini_d = g.w_last_d = g.w_change_d = direction
        self.raw = raw.copy()
        return self.raw.copy()

    def set_goal(self, goal_xy):
        if self.raw is None:
            raise RuntimeError("reset(seed, wind_degrees) is required")
        goal = np.asarray(goal_xy, dtype=np.float32)
        if goal.shape != (2,) or not np.isfinite(goal).all():
            raise ValueError("Goal must be two finite world coordinates")
        self.env.state[12:14] = goal
        self.modules.globals.state[12:14] = goal
        self.raw[12:14] = goal

    def step(self, normalized_command):
        if self.raw is None:
            raise RuntimeError("reset(seed, wind_degrees) is required")
        command = np.asarray(normalized_command)
        if command.shape != (2,) or not np.isfinite(command).all():
            raise ValueError("Command must be two finite normalized actuator increments")
        high = self.env.action_space.high.astype(np.float64)
        physical = self.modules.network.Action_adapter(command, high)
        with self._rng():
            raw, reward, terminated, inherited_truncated, info = self.env.step(physical)
        if "integration_failed" not in info or not isinstance(info["integration_failed"], (bool, np.bool_)):
            raise UpstreamStepMismatch("Adapted step did not report a boolean integration failure")
        failed = bool(info["integration_failed"])
        if bool(inherited_truncated) != failed:
            raise UpstreamStepMismatch("Adapted truncation differs from integration failure")
        self.raw = raw.copy()
        if not np.isfinite(self.raw).all() or not np.isfinite(reward):
            raise FloatingPointError("Non-finite continuous environment transition")
        g = self.modules.globals
        time_limit = float(g.current_time) >= self.total_time_limit
        radius = float(np.hypot(self.raw[0], self.raw[1]))
        radius_limit = radius >= self.world_radius_limit
        info = dict(info)
        info.update({
            "time": float(g.current_time), "physical_action": np.asarray(physical).copy(),
            "raw": self.raw.copy(), "world_radius": radius,
            "total_time_limit_reached": bool(time_limit),
            "world_radius_limit_reached": bool(radius_limit),
            "legacy_radius_limit_reached": radius >= 750.0,
            "legacy_time_limit_reached": float(g.current_time) >= float(g.total_time),
            "legacy_limits_enforced": False,
            "goal_reached": bool(terminated),
        })
        return self.raw.copy(), float(reward), bool(terminated), bool(failed or time_limit or radius_limit), info

    def continuity_snapshot(self):
        """JSON-safe physical continuity evidence; never a planner input."""
        if self.raw is None:
            raise RuntimeError("reset(seed, wind_degrees) is required")
        g = self.modules.globals
        return {
            "state": self.env.state[:12].astype(float).tolist(),
            "target_sail_angle": float(self.env.target_sail_angle),
            "target_rudder_angle": float(self.env.target_rudder_angle),
            "time": float(g.current_time),
            "dryden": [float(self.env.dryden_state_u), float(self.env.dryden_state_v)],
            "wind": [float(g.w_change_v), float(g.w_change_d)],
            "rng_sha256": hashlib.sha256(pickle.dumps(
                (self.random_state, self.numpy_state), protocol=4)).hexdigest(),
            "gym_rng_sha256": hashlib.sha256(pickle.dumps(
                self.env.np_random.bit_generator.state, protocol=4)).hexdigest(),
        }

    def close(self):
        self.env.close()
