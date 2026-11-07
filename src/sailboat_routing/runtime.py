"""Frozen fourth-chapter inference; all runtime code/assets belong to NEW_ROOT."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]


def configure_cpu() -> None:
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
    os.environ["XDG_CACHE_HOME"] = str(ROOT / ".cache")
    os.environ["TMPDIR"] = str(ROOT / ".tmp")
    sys.dont_write_bytecode = True


configure_cpu()
import numpy as np
import torch

torch.set_num_threads(1)


def _load(name: str, path: Path):
    path = path.resolve(strict=True)
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Runtime dependency outside NEW_ROOT: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SeniorModules:
    """Separate globals per simulator; no source path or Gym registry mutation."""

    def __init__(self, directory: Path | None = None):
        directory = directory or ROOT / "third_party/senior"
        self.globals = _load("senior_globals", directory / "globals.py")
        previous = sys.modules.get("globals")
        sys.modules["globals"] = self.globals
        try:
            self.network = _load("senior_network", directory / "utils_lstm.py")
            self.noise = _load("senior_noise", directory / "noise_utils_nowind.py")
            self.environment = _load("senior_environment", directory / "sailboat_s14.py")
        finally:
            if previous is None:
                sys.modules.pop("globals", None)
            else:
                sys.modules["globals"] = previous
        self.paths = {name: str(module.__file__) for name, module in (
            ("globals", self.globals), ("network", self.network),
            ("noise", self.noise), ("environment", self.environment))}


@dataclass(frozen=True)
class Decision:
    action: np.ndarray
    features: np.ndarray | None
    history_steps: int


class FrozenController:
    def __init__(self, modules: SeniorModules, actor_path: Path, normalizer_path: Path):
        self.modules = modules
        self.actor = modules.network.Actor(14, 2, (256, 256)).cpu()
        self.actor.load_state_dict(torch.load(actor_path, map_location="cpu", weights_only=True), strict=True)
        self.actor.eval().requires_grad_(False)
        self.normalizer = modules.network.ZScoreNormalizer(14, torch.device("cpu"))
        state = torch.load(normalizer_path, map_location="cpu", weights_only=True)
        if state["mean"].shape != (14,) or state["var"].shape != (14,):
            raise ValueError("This runtime requires the matching 14-dimensional normalizer")
        if not torch.isfinite(state["mean"]).all() or not torch.isfinite(state["var"]).all():
            raise ValueError("Non-finite normalizer")
        if (state["var"] < 0).any() or state["count"] <= 0:
            raise ValueError("Invalid normalizer statistics")
        self.normalizer.load_state_dict(state)
        self._feature = None
        self._capture = False
        self._hook = self.actor.lstm_ln.register_forward_hook(self._record_feature)
        self.steps = 0
        self.previous = None
        self.previous_action = np.zeros(2, dtype=np.float32)

    def _record_feature(self, module, inputs, output):
        if self._capture:
            self._feature = output[0, -1].detach().cpu().numpy().copy()

    def reset(self, initial_observation: np.ndarray) -> None:
        self.actor.reset_hidden_state()
        self.previous = np.asarray(initial_observation, dtype=np.float32).copy()
        self.previous_action = np.zeros(2, dtype=np.float32)
        self.steps = 0
        self._feature = None

    def act(self, observation: np.ndarray, *, record_features: bool = False) -> Decision:
        observation = np.asarray(observation, dtype=np.float32)
        if self.previous is None:
            raise RuntimeError("reset(initial_observation) is required")
        if observation.shape != (14,) or not np.isfinite(observation).all():
            raise ValueError("Expected finite 14-dimensional observation")
        self._capture = record_features
        with torch.inference_mode():
            current = self.normalizer.normalize(torch.from_numpy(observation).unsqueeze(0))
            previous = self.normalizer.normalize(torch.from_numpy(self.previous).unsqueeze(0))
            action, _ = self.actor(current_state=current, prev_state=previous,
                prev_action=torch.from_numpy(self.previous_action).unsqueeze(0),
                deterministic=True, with_logprob=False, single_step_mode=True,
                env_ids=["v0"])
            action = action[0].cpu().numpy().copy()
            features = (np.concatenate((current[0].cpu().numpy(), self._feature))
                        if record_features else None)
        self._capture = False
        if not np.isfinite(action).all():
            raise FloatingPointError("Non-finite frozen Actor action")
        self.previous = observation.copy()
        self.previous_action = action.copy()
        self.steps += 1
        return Decision(action, features, self.steps)

    def hidden(self) -> tuple[np.ndarray, np.ndarray]:
        return tuple(value.detach().cpu().numpy().copy()
                     for value in self.actor.hidden_states["v0"])

    def close(self) -> None:
        self._hook.remove()


class OriginalSegment:
    """Original 500 m task, original dynamics/noise/action units, isolated RNG."""

    def __init__(self, modules: SeniorModules, *, noise_enabled: bool = True):
        self.modules = modules
        self.env = modules.environment.Sailboat_nowind_last(render_mode=None)
        self.noise_enabled = noise_enabled
        self.random_state = None
        self.numpy_state = None

    @contextmanager
    def _rng(self):
        old_python, old_numpy = random.getstate(), np.random.get_state()
        random.setstate(self.random_state)
        np.random.set_state(self.numpy_state)
        try:
            yield
        finally:
            self.random_state, self.numpy_state = random.getstate(), np.random.get_state()
            random.setstate(old_python)
            np.random.set_state(old_numpy)

    def reset(self, seed: int, wind_degrees: float | None = None):
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
        self.noise = self.modules.noise.NoiseManager(sensor_noise_ratio=0.03,
            actuator_noise_ratio=0.03, enable_sensor_noise=self.noise_enabled,
            enable_actuator_noise=self.noise_enabled, seed=seed)
        self.raw = raw.copy()
        return self.noise.add_observation_noise(self.raw).copy()

    def step(self, command: np.ndarray):
        high = self.env.action_space.high.astype(float)
        normalized = self.noise.add_action_noise(command, high)
        physical = self.modules.network.Action_adapter(normalized, high)
        with self._rng():
            raw, reward, terminated, truncated, info = self.env.step(physical)
        self.raw = raw.copy()
        observation = self.noise.add_observation_noise(self.raw).copy()
        if not np.isfinite(self.raw).all() or not np.isfinite(reward):
            raise FloatingPointError("Non-finite original environment transition")
        return observation, float(reward), bool(terminated), bool(truncated), {
            "raw": self.raw.copy(), "physical_action": np.asarray(physical).copy(),
            "time": float(self.modules.globals.current_time),
        }

    def close(self):
        self.env.close()
