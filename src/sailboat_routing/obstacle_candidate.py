"""Isolated 0204@10800 candidate; never replaces the fourth-chapter runtime."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
import random
import sys
from types import SimpleNamespace

from .runtime import ROOT, _load, configure_cpu, Decision
import numpy as np
import torch

SNAPSHOT = ROOT / "third_party/obstacle_candidate"
ASSETS = ROOT / "checkpoints/obstacle_candidate"
PREFIX = "saclstm_s14obst_noise_0204"
MODES = ("legacy_training", "eval")


def protocol_manifest():
    files = sorted(SNAPSHOT.glob("*.py")) + sorted(ASSETS.glob("*.pth"))
    return {
        "candidate": "0204@10800", "observation_dim": 18,
        "environment_class": "sailboat_s14_obst_V3:Sailboat_obst_v3",
        "requested_gym_id": "sailboat-s14-obst-v3",
        "gym_registration_status": "not present in SOURCE_ROOT .venv gym registry; direct audited class used",
        "history": "persistent single_step; previous noisy observation and raw normalized action; LN output deque 10, zero padded",
        "action": "tanh -> original actuator noise(normalized, max radians) -> multiply max radians -> V3 floor to whole degrees",
        "normalization": "frozen (x-mean)/(sqrt(var)+1e-6)",
        "dropout": "p=0.1; original scripts retain training mode even deterministic=True",
        "interface_adaptations": ["explicit independent Python/NumPy RNG streams because reset(seed) does not seed global random", "explicit wind and fixed obstacle overrides after original reset"],
        "hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    }


def loading_paths():
    return {"snapshot": str(SNAPSHOT), "actor": str(ASSETS / f"{PREFIX}_actor10800.pth"),
            "normalizer": str(ASSETS / f"{PREFIX}_normalizer10800.pth")}


class CandidateModules:
    def __init__(self):
        configure_cpu()
        self.globals = _load("obstacle_globals", SNAPSHOT / "globals.py")
        previous = {k: sys.modules.get(k) for k in ("globals", "utils_lstm_att_normal")}
        sys.modules["globals"] = self.globals
        try:
            self.network = _load("obstacle_network", SNAPSHOT / "utils_lstm_att_normal.py")
            sys.modules["utils_lstm_att_normal"] = self.network
            self.original = _load("obstacle_original", SNAPSHOT / "SAC_lstm_att_normal.py")
            self.noise = _load("obstacle_noise", SNAPSHOT / "noise_utils.py")
            self.environment = _load("obstacle_environment", SNAPSHOT / "sailboat_s14_obst_V3.py")
        finally:
            for key, value in previous.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value
        self.paths = {k: str(getattr(self, k).__file__) for k in ("globals", "network", "original", "noise", "environment")}


def observation(value):
    result = np.asarray(value, dtype=np.float32)
    if result.shape != (18,) or not np.isfinite(result).all():
        raise ValueError("Expected finite 18D obstacle observation")
    return result


class ObstacleController:
    def __init__(self, modules=None, *, mode="legacy_training", actor_path=None, normalizer_path=None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.modules = modules or CandidateModules()
        paths = loading_paths()
        actor_path = Path(actor_path or paths["actor"]).resolve(strict=True)
        normalizer_path = Path(normalizer_path or paths["normalizer"]).resolve(strict=True)
        if not all(p.is_relative_to(ROOT) for p in (actor_path, normalizer_path)):
            raise ValueError("Candidate assets must belong to NEW_ROOT")
        self.actor = self.modules.network.Actor(18, 2, (256, 256)).cpu()
        self.actor.load_state_dict(torch.load(actor_path or paths["actor"], map_location="cpu", weights_only=True), strict=True)
        self.actor.requires_grad_(False).train(mode == "legacy_training")
        self.mode = mode
        state = torch.load(normalizer_path or paths["normalizer"], map_location="cpu", weights_only=True)
        if set(state) != {"mean", "var", "count"}:
            raise ValueError("Unexpected normalizer fields")
        for name in ("mean", "var"):
            if state[name].shape != (18,) or not torch.isfinite(state[name]).all():
                raise ValueError("Invalid 18D normalizer")
        if (state["var"] < 0).any() or state["count"] <= 0:
            raise ValueError("Invalid frozen statistics")
        self.normalizer = self.modules.network.ZScoreNormalizer(18, torch.device("cpu"))
        self.normalizer.load_state_dict(state)
        self.previous = None
        self.feature = None
        self._capture = False
        self._hook = self.actor.lstm_ln.register_forward_hook(self._record)

    def _record(self, module, inputs, output):
        if self._capture:
            self.feature = output[0, -1].detach().cpu().numpy().copy()

    def reset(self, initial):
        self.previous = observation(initial).copy()
        self.previous_action = np.zeros(2, dtype=np.float32)
        self.actor.reset_hidden_state()
        self.steps = 0
        self.feature = None

    def act(self, current, *, record_features=False):
        current = observation(current)
        if self.previous is None:
            raise RuntimeError("reset(initial) required")
        self._capture = record_features
        try:
            with torch.no_grad():
                action, _ = self.actor(
                    current_state=self.normalizer.normalize(torch.from_numpy(current[None])),
                    prev_state=self.normalizer.normalize(torch.from_numpy(self.previous[None])),
                    prev_action=torch.from_numpy(self.previous_action[None]), deterministic=True,
                    with_logprob=False, env_ids=["v0"], single_step_mode=True)
                action = action[0].cpu().numpy().copy()
        finally:
            self._capture = False
        if not np.isfinite(action).all():
            raise FloatingPointError("Non-finite candidate action")
        self.previous = current.copy()
        self.previous_action = action.copy()
        self.steps += 1
        features = np.concatenate((self.normalizer.normalize(torch.from_numpy(current)).numpy(), self.feature)) if record_features else None
        return Decision(action, features, self.steps)

    def history(self):
        h, c = self.actor.hidden_states["v0"]
        return {"h": h.detach().numpy().copy(), "c": c.detach().numpy().copy(),
                "attention_history": torch.stack(list(self.actor.lstm_output_history["v0"])).detach().numpy().copy()}

    def hidden(self):
        state = self.history()
        return state["h"], state["c"]

    def reference(self):
        """Run untouched select_action without constructing learner/replay/critic."""
        return SimpleNamespace(actor=self.actor, state_normalizer=self.normalizer, dvc=torch.device("cpu"))

    def close(self):
        self._hook.remove()


class ObstacleSegment:
    def __init__(self, modules=None, *, noise_enabled=True):
        self.modules = modules or CandidateModules()
        self.noise_enabled = noise_enabled
        # Constructor itself resets using global Python RNG; restore caller state.
        old = random.getstate()
        try:
            self.env = self.modules.environment.Sailboat_obst_v3(render_mode=None)
        finally:
            random.setstate(old)

    @contextmanager
    def _rng(self):
        old_py, old_np = random.getstate(), np.random.get_state()
        random.setstate(self.python_rng)
        np.random.set_state(self.numpy_rng)
        try:
            yield
        finally:
            self.python_rng, self.numpy_rng = random.getstate(), np.random.get_state()
            random.setstate(old_py)
            np.random.set_state(old_np)

    def reset(self, seed=0, wind_degrees=0, obstacles=None):
        self.python_rng = random.Random(seed).getstate()
        self.numpy_rng = np.random.RandomState(seed).get_state()
        with self._rng():
            raw, _ = self.env.reset(seed=seed)
        g = self.modules.globals
        direction = float(np.deg2rad(wind_degrees))
        g.w0 = [8., direction]
        g.w_ini_v = g.w_last_v = g.w_change_v = 8.
        g.w_ini_d = g.w_last_d = g.w_change_d = direction
        if obstacles is not None:
            g.obstacles = [tuple(map(float, p)) for p in obstacles]
            g.observed_obstacles = []
        self.noise = self.modules.noise.NoiseManager(sensor_noise_ratio=.03, actuator_noise_ratio=.03,
            enable_sensor_noise=self.noise_enabled, enable_actuator_noise=self.noise_enabled, seed=seed)
        self.raw = observation(raw).copy()
        return self.noise.add_observation_noise(self.raw).copy()

    def step(self, action):
        action = np.asarray(action)
        if action.shape != (2,) or not np.isfinite(action).all() or (np.abs(action) > 1).any():
            raise ValueError("Expected finite normalized action in [-1,1]")
        high = self.env.action_space.high.astype(float)
        noisy = self.noise.add_action_noise(action, high)
        physical = self.modules.network.Action_adapter(noisy, high)
        with self._rng():
            raw, reward, terminated, truncated, info = self.env.step(physical)
        self.raw = observation(raw).copy()
        if not np.isfinite(reward):
            raise FloatingPointError("Non-finite V3 reward")
        return self.noise.add_observation_noise(self.raw).copy(), float(reward), bool(terminated), bool(truncated), {"raw": self.raw.copy(), "physical_action": physical.copy(), "time": float(self.modules.globals.current_time)}

    def close(self):
        self.env.close()
