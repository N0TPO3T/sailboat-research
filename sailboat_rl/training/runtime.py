"""Long-run runtime support for canonical training.

Training checkpoints restore learner and replay state, then training resumes from
freshly reset environments. They do not serialize live simulator/VecEnv state.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import shutil
import signal
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
import torch


CHECKPOINT_SCHEMA_VERSION = 1
RESUME_CONFIG_KEYS = (
    "replay_capacity",
    "gamma",
    "net_width",
    "a_lr",
    "c_lr",
    "batch_size",
    "alpha",
    "adaptive_alpha",
    "update_every",
    "learning_starts",
    "num_envs",
    "enable_sensor_noise",
    "enable_actuator_noise",
    "sensor_noise_ratio",
    "actuator_noise_ratio",
    "actor_inference_backend",
    "strict_deterministic",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seed_everything(master_seed: int, strict_deterministic: bool = False) -> None:
    random.seed(master_seed)
    np.random.seed(master_seed)
    torch.manual_seed(master_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(master_seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(bool(strict_deterministic))


def seed_worker_environment(env, worker_seed: int) -> None:
    random.seed(worker_seed)
    np.random.seed(worker_seed)
    torch.manual_seed(worker_seed)
    env.action_space.seed(worker_seed)
    env.observation_space.seed(worker_seed)
    env.reset(seed=worker_seed)


def capture_rng_state() -> dict[str, Any]:
    state = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def restore_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"].cpu())
    if "torch_cuda" in state and torch.cuda.is_available():
        torch.cuda.set_rng_state_all([item.cpu() for item in state["torch_cuda"]])


def capture_noise_rng_state(noise_manager) -> dict[str, Any]:
    return {
        "sensor": noise_manager.sensor_noise.rng.get_state(),
        "actuator": noise_manager.actuator_noise.rng.get_state(),
    }


def restore_noise_rng_state(noise_manager, state: dict[str, Any]) -> None:
    noise_manager.sensor_noise.rng.set_state(state["sensor"])
    noise_manager.actuator_noise.rng.set_state(state["actuator"])


def _to_cpu(value: Any) -> Any:
    if torch.is_tensor(value):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: _to_cpu(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_cpu(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_to_cpu(item) for item in value)
    return value


def _optimizer_to_device(optimizer, device: torch.device) -> None:
    for values in optimizer.state.values():
        for key, value in values.items():
            if torch.is_tensor(value):
                values[key] = value.to(device)


def trainer_state_dict(agent) -> dict[str, Any]:
    state = {
        "actor": _to_cpu(agent.actor.state_dict()),
        "q_critic": _to_cpu(agent.q_critic.state_dict()),
        "q_critic_target": _to_cpu(agent.q_critic_target.state_dict()),
        "actor_optimizer": _to_cpu(agent.actor_optimizer.state_dict()),
        "q_critic_optimizer": _to_cpu(agent.q_critic_optimizer.state_dict()),
        "normalizer": _to_cpu(agent.state_normalizer.state_dict()),
        "adaptive_alpha": bool(agent.adaptive_alpha),
        "alpha": float(agent.alpha.item() if hasattr(agent.alpha, "item") else agent.alpha),
        "training_step": int(agent.training_step),
        "critic_update_count": int(agent.critic_update_count),
        "actor_update_count": int(agent.actor_update_count),
        "alpha_update_count": int(agent.alpha_update_count),
        "policy_update_freq": int(agent.policy_update_freq),
        "critic_warmup_steps": int(agent.critic_warmup_steps),
        "loss_history_tail": {
            "q": list(agent.q_loss_history[-1000:]),
            "actor": list(agent.a_loss_history[-1000:]),
            "alpha": list(agent.alpha_loss_history[-1000:]),
        },
    }
    if agent.adaptive_alpha:
        state.update({
            "log_alpha": _to_cpu(agent.log_alpha),
            "alpha_optimizer": _to_cpu(agent.alpha_optim.state_dict()),
        })
    return state


def load_trainer_state_dict(agent, state: dict[str, Any]) -> None:
    if bool(state["adaptive_alpha"]) != bool(agent.adaptive_alpha):
        raise ValueError("Adaptive-alpha configuration differs from the resume checkpoint")
    if int(state["policy_update_freq"]) != int(agent.policy_update_freq):
        raise ValueError("Policy update frequency differs from the resume checkpoint")

    agent.actor.load_state_dict(state["actor"])
    agent.q_critic.load_state_dict(state["q_critic"])
    agent.q_critic_target.load_state_dict(state["q_critic_target"])
    agent.actor_optimizer.load_state_dict(state["actor_optimizer"])
    agent.q_critic_optimizer.load_state_dict(state["q_critic_optimizer"])
    _optimizer_to_device(agent.actor_optimizer, agent.dvc)
    _optimizer_to_device(agent.q_critic_optimizer, agent.dvc)
    agent.state_normalizer.load_state_dict(state["normalizer"])

    if agent.adaptive_alpha:
        with torch.no_grad():
            agent.log_alpha.copy_(state["log_alpha"].to(agent.dvc))
        agent.alpha_optim.load_state_dict(state["alpha_optimizer"])
        _optimizer_to_device(agent.alpha_optim, agent.dvc)
        agent.alpha = agent.log_alpha.exp()
    else:
        agent.alpha = float(state["alpha"])

    agent.training_step = int(state["training_step"])
    agent.critic_update_count = int(state["critic_update_count"])
    inferred_policy_updates = agent.critic_update_count // agent.policy_update_freq
    agent.actor_update_count = int(state.get("actor_update_count", inferred_policy_updates))
    agent.alpha_update_count = int(
        state.get("alpha_update_count", inferred_policy_updates if agent.adaptive_alpha else 0)
    )
    agent.critic_warmup_steps = int(state["critic_warmup_steps"])
    history = state.get("loss_history_tail", {})
    agent.q_loss_history = list(history.get("q", []))
    agent.a_loss_history = list(history.get("actor", []))
    agent.alpha_loss_history = list(history.get("alpha", []))


def _torch_save_fsync(value: Any, path: Path) -> None:
    with path.open("wb") as handle:
        torch.save(value, handle)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def resolve_resume_checkpoint(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if candidate.is_file() and candidate.name == "latest.json":
        with candidate.open("r", encoding="utf-8") as handle:
            latest = json.load(handle)
        return candidate.parent / latest["checkpoint"]
    if (candidate / "trainer_state.pt").is_file():
        return candidate
    latest_path = candidate / "checkpoints" / "latest.json"
    if latest_path.is_file():
        with latest_path.open("r", encoding="utf-8") as handle:
            latest = json.load(handle)
        return latest_path.parent / latest["checkpoint"]
    raise FileNotFoundError(f"No resumable checkpoint found at {candidate}")


def run_directory(output_dir: Path, model_prefix: str, requested: Path | None, resume: Path | None) -> Path:
    if requested is not None:
        return requested.expanduser().resolve()
    if resume is not None:
        checkpoint = resolve_resume_checkpoint(resume)
        if checkpoint.parent.name != "checkpoints":
            raise ValueError(f"Unexpected checkpoint layout: {checkpoint}")
        return checkpoint.parent.parent
    return (output_dir / "runs" / model_prefix).resolve()


def save_training_checkpoint(
    agent,
    run_dir: Path,
    total_steps: int,
    completed_episodes: int,
    noise_manager,
    extra_counters: dict[str, Any] | None = None,
) -> Path:
    checkpoints_dir = run_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_name = f"step_{int(total_steps):012d}"
    final_dir = checkpoints_dir / checkpoint_name
    if final_dir.exists():
        atomic_write_json(
            {"checkpoint": checkpoint_name, "total_steps": int(total_steps)},
            checkpoints_dir / "latest.json",
        )
        return final_dir

    temporary_dir = checkpoints_dir / f".{checkpoint_name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    temporary_dir.mkdir()
    try:
        trainer = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "saved_at": utc_now(),
            "total_steps": int(total_steps),
            "completed_episodes": int(completed_episodes),
            "extra_counters": dict(extra_counters or {}),
            "agent": trainer_state_dict(agent),
            "rng": capture_rng_state(),
            "noise_rng": capture_noise_rng_state(noise_manager),
        }
        _torch_save_fsync(trainer, temporary_dir / "trainer_state.pt")
        del trainer

        replay = agent.replay_buffer.state_dict()
        _torch_save_fsync(replay, temporary_dir / "replay_state.pt")
        replay_size = int(replay["size"])
        replay_capacity = int(replay["max_size"])
        max_priority = float(replay["max_priority"])
        del replay

        checkpoint_manifest = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "saved_at": utc_now(),
            "resume_semantics": "learner-and-replay-state; environments reset on process resume",
            "total_steps": int(total_steps),
            "completed_episodes": int(completed_episodes),
            "replay_size": replay_size,
            "replay_capacity": replay_capacity,
            "max_priority": max_priority,
            "files": {
                "trainer_state.pt": (temporary_dir / "trainer_state.pt").stat().st_size,
                "replay_state.pt": (temporary_dir / "replay_state.pt").stat().st_size,
            },
        }
        atomic_write_json(checkpoint_manifest, temporary_dir / "manifest.json")
        _fsync_directory(temporary_dir)
        os.replace(temporary_dir, final_dir)
        _fsync_directory(checkpoints_dir)
        atomic_write_json(
            {"checkpoint": checkpoint_name, "total_steps": int(total_steps)},
            checkpoints_dir / "latest.json",
        )
        return final_dir
    except Exception:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
        raise


def load_training_checkpoint(agent, checkpoint_path: Path, noise_manager) -> dict[str, Any]:
    checkpoint = resolve_resume_checkpoint(checkpoint_path)
    manifest_path = checkpoint / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Incomplete checkpoint without manifest: {checkpoint}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        checkpoint_manifest = json.load(handle)
    if int(checkpoint_manifest["schema_version"]) != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported checkpoint schema: {checkpoint_manifest['schema_version']}")

    trainer = torch.load(checkpoint / "trainer_state.pt", map_location=agent.dvc, weights_only=False)
    replay = torch.load(checkpoint / "replay_state.pt", map_location="cpu", weights_only=False)
    load_trainer_state_dict(agent, trainer["agent"])
    agent.replay_buffer.load_state_dict(replay)
    restore_noise_rng_state(noise_manager, trainer["noise_rng"])
    restore_rng_state(trainer["rng"])
    return {
        "checkpoint": checkpoint,
        "total_steps": int(trainer["total_steps"]),
        "completed_episodes": int(trainer["completed_episodes"]),
        "extra_counters": dict(trainer.get("extra_counters", {})),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, torch.device):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _git_state(repo_root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def _source_hashes(paths: list[Path], repo_root: Path) -> dict[str, str]:
    hashes = {}
    for path in paths:
        resolved = path.resolve()
        try:
            display_path = resolved.relative_to(repo_root.resolve())
        except ValueError:
            display_path = resolved
        hashes[str(display_path)] = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return hashes


def prepare_run_manifest(
    run_dir: Path,
    repo_root: Path,
    model_family: str,
    environment_id: str,
    model_prefix: str,
    master_seed: int,
    config: dict[str, Any],
    device: torch.device,
    source_paths: list[Path],
    resume_source: Path | None,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "run_manifest.json"
    if resume_source is not None:
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Cannot preserve run identity without {manifest_path}")
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        expected = {
            "model_family": model_family,
            "environment_id": environment_id,
            "model_prefix": model_prefix,
            "master_seed": int(master_seed),
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise ValueError(f"Resume identity mismatch for {key}: {manifest.get(key)!r} != {value!r}")
        saved_config = manifest.get("config", {})
        current_config = _json_safe(config)
        for key in RESUME_CONFIG_KEYS:
            saved_value = saved_config.get(key)
            if key == "actor_inference_backend" and key not in saved_config:
                saved_value = "serial"
            if saved_value != current_config.get(key):
                raise ValueError(
                    f"Resume configuration mismatch for {key}: "
                    f"{saved_value!r} != {current_config.get(key)!r}"
                )
        manifest.setdefault("resume_events", []).append({
            "at": utc_now(),
            "source": str(resolve_resume_checkpoint(resume_source)),
        })
        atomic_write_json(manifest, manifest_path)
        return manifest_path

    if manifest_path.exists():
        raise FileExistsError(f"Run already exists; use --resume to continue it: {run_dir}")

    gpu_name = None
    if device.type == "cuda" and torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(device)
    manifest = {
        "schema_version": 1,
        "model_family": model_family,
        "environment_id": environment_id,
        "model_prefix": model_prefix,
        "master_seed": int(master_seed),
        "worker_seed_rule": "master_seed + worker_rank",
        "strict_deterministic": bool(config.get("strict_deterministic", False)),
        "config": _json_safe(config),
        "buffer_capacity": int(config["replay_capacity"]),
        "history_length": 10 if model_family == "SAC-LSTM" else None,
        "device": str(device),
        "start_time": utc_now(),
        "git": _git_state(repo_root),
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "gymnasium": gym.__version__,
            "cuda": torch.version.cuda,
            "gpu_name": gpu_name,
        },
        "output_directory": str(run_dir),
        "resume_source": None,
        "resume_events": [],
        "source_sha256": _source_hashes(source_paths, repo_root),
    }
    atomic_write_json(manifest, manifest_path)
    return manifest_path


class GracefulStop:
    """Signal handler that only records intent; serialization stays in the train loop."""

    def __init__(self):
        self.requested = False
        self.signal_number: int | None = None
        self._previous: dict[int, Any] = {}

    def _handle(self, signum, _frame) -> None:
        self.requested = True
        self.signal_number = int(signum)

    def install(self) -> None:
        for signum in (signal.SIGINT, signal.SIGTERM):
            self._previous[signum] = signal.getsignal(signum)
            signal.signal(signum, self._handle)

    def restore(self) -> None:
        for signum, handler in self._previous.items():
            signal.signal(signum, handler)
        self._previous.clear()
