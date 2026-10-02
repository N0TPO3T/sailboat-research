"""Rigid 500 m target frames and causal reconstruction of frozen Actor memory."""
from __future__ import annotations

from dataclasses import dataclass
import math
from time import perf_counter
from typing import TYPE_CHECKING, Sequence

import numpy as np
import torch

if TYPE_CHECKING:
    from .runtime import FrozenController


def _vector(value, size: int, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"{name} must be a finite {size}-vector")
    return result


def _wrap(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


@dataclass(frozen=True)
class LocalFrame:
    """A rigid world-to-controller transform; lengths remain physical metres."""

    goal_world: tuple[float, float]
    angle: float
    origin: tuple[float, float]

    @classmethod
    def for_leg(cls, start_xy, goal_xy) -> LocalFrame:
        start = _vector(start_xy, 2, "start_xy")
        goal = _vector(goal_xy, 2, "goal_xy")
        delta = goal - start
        if not np.any(delta):
            raise ValueError("A leg requires distinct start and goal positions")
        angle = math.atan2(delta[1], delta[0])
        origin = goal - 500.0 * np.array([math.cos(angle), math.sin(angle)])
        return cls(tuple(goal), angle, tuple(origin))

    def world_to_local(self, xy) -> np.ndarray:
        x, y = _vector(xy, 2, "world_xy") - self.origin
        c, s = math.cos(self.angle), math.sin(self.angle)
        return np.array([c * x + s * y, -s * x + c * y])

    def local_to_world(self, xy) -> np.ndarray:
        x, y = _vector(xy, 2, "local_xy")
        c, s = math.cos(self.angle), math.sin(self.angle)
        return np.array([c * x - s * y, s * x + c * y]) + self.origin

    def wind_to_local(self, direction: float) -> float:
        """Rotate a world wind direction in radians; retain its to/from convention."""
        return _wrap(float(direction) - self.angle)

    def wind_to_world(self, direction: float) -> float:
        return _wrap(float(direction) + self.angle)

    def encode(self, raw14, previous_raw14_or_None=None) -> np.ndarray:
        raw = _vector(raw14, 14, "raw14")
        local_xy = self.world_to_local(raw[:2])
        encoded = raw.astype(np.float32)
        encoded[:2] = local_xy
        encoded[3] = _wrap(float(raw[3]) - self.angle)
        encoded[12:14] = (500.0, 0.0)
        encoded[10:12] = 0.0
        if previous_raw14_or_None is not None:
            previous = _vector(previous_raw14_or_None, 14, "previous_raw14")
            previous_xy = self.world_to_local(previous[:2])
            target = np.array([500.0, 0.0])
            encoded[10] = np.linalg.norm(previous_xy - target) - np.linalg.norm(local_xy - target)
            encoded[11] = abs(previous_xy[0] - 500.0) - abs(local_xy[0] - 500.0)
        return encoded


def reencode_controller(
    controller: FrozenController,
    frame: LocalFrame,
    raw_history: Sequence[np.ndarray],
    commands: Sequence[np.ndarray],
) -> tuple[np.ndarray, float]:
    """Rebuild memory BEFORE the current decision, never recomputing past controls.

    ``raw_history`` contains s_0 through s_t; ``commands`` contains the actual
    normalized Actor commands a_0 through a_{t-1} (before actuator noise).
    The original first recurrent input is (s_0, zero), not an empty history.
    Replay makes exactly t forwards, leaving decision t to the caller.
    """
    started = perf_counter()
    t = len(commands)
    if len(raw_history) != t + 1:
        raise ValueError("raw_history must contain exactly len(commands) + 1 observations")
    encoded = [frame.encode(raw, None if i == 0 else raw_history[i - 1])
               for i, raw in enumerate(raw_history)]
    actual_commands = [_vector(action, 2, "command").astype(np.float32)
                       for action in commands]
    zero = np.zeros(2, dtype=np.float32)
    capture = controller._capture
    controller._capture = False
    try:
        controller.actor.reset_hidden_state()
        with torch.inference_mode():
            for i in range(t):
                previous = encoded[0 if i == 0 else i - 1]
                previous_action = zero if i == 0 else actual_commands[i - 1]
                controller.actor(
                    current_state=controller.normalizer.normalize(
                        torch.from_numpy(encoded[i]).unsqueeze(0)),
                    prev_state=controller.normalizer.normalize(
                        torch.from_numpy(previous).unsqueeze(0)),
                    prev_action=torch.from_numpy(previous_action).unsqueeze(0),
                    deterministic=True, with_logprob=False,
                    single_step_mode=True, env_ids=["v0"],
                )
        controller.previous = encoded[-2].copy() if t else encoded[0].copy()
        controller.previous_action = actual_commands[-1].copy() if t else zero
        controller.steps = t
    finally:
        controller._capture = capture
    return encoded[-1], perf_counter() - started
