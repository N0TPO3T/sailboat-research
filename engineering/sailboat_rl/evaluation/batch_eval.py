"""
Batch evaluator for seed-ablation SAC/SAC-LSTM sailboat checkpoints.

The script is config-driven and writes CSV-only evaluation artifacts:
per-episode records, grouped summaries, boxplot-ready values, and a JSON
manifest. It intentionally loads only Actor + normalizer for evaluation to
avoid allocating the large training ReplayBuffer in every worker process.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import random
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_MODEL_DIR = REPO_ROOT / "canonical_runs" / "model"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "canonical_runs" / "evaluation"

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import gymnasium as gym
import numpy as np
import torch

from sailboat_rl.envs import globals


SUCCESS_DISTANCE_M = 10.0
ACTION_SECONDS = 1.0
WILSON_Z_95 = 1.96


@dataclass(frozen=True)
class ModelSpec:
    enabled: bool
    model_id: str
    model_family: str
    algo_type: str
    env_name: str
    model_prefix: str
    model_step: int
    net_width: int
    noise_type: str
    eval_seed: int


@dataclass(frozen=True)
class ScenarioSpec:
    scenario: str
    scenario_group: str
    target_wind_deg: float | None
    num_episodes: int
    seed_offset: int


@dataclass(frozen=True)
class WorkerTask:
    task_id: str
    model: ModelSpec
    scenario: ScenarioSpec
    episode_ids: tuple[int, ...]
    model_dir: str
    max_steps: int
    dvc: str
    enable_sensor_noise: bool
    enable_actuator_noise: bool
    sensor_noise_ratio: float
    actuator_noise_ratio: float


class EvalPolicy:
    def __init__(self, spec: ModelSpec, env, model_dir: Path, device: torch.device):
        self.spec = spec
        self.device = device
        self.max_action = env.action_space.high.astype(float)
        self.action_dim = env.action_space.shape[0]
        self.state_dim = env.observation_space.shape[0]

        if spec.algo_type == "lstm":
            from sailboat_rl.algorithms.utils_lstm import Actor, Action_adapter, ZScoreNormalizer

            self.actor = Actor(self.state_dim, self.action_dim, (spec.net_width, 256)).to(device)
            self.normalizer = ZScoreNormalizer(self.state_dim, device)
            self.action_adapter = Action_adapter
        elif spec.algo_type == "fc":
            from sailboat_rl.algorithms.utils_fc import Actor, Action_adapter, ZScoreNormalizer

            self.actor = Actor(self.state_dim, self.action_dim, (spec.net_width, 512, 256)).to(device)
            self.normalizer = ZScoreNormalizer(self.state_dim, device)
            self.action_adapter = Action_adapter
        else:
            raise ValueError(f"Unsupported algo_type: {spec.algo_type}")

        actor_path = model_dir / f"{spec.model_prefix}_actor{spec.model_step}.pth"
        normalizer_path = model_dir / f"{spec.model_prefix}_normalizer{spec.model_step}.pth"
        self.actor.load_state_dict(torch.load(actor_path, map_location=device))
        self.normalizer.load_state_dict(torch.load(normalizer_path, map_location=device))
        self.actor.eval()

    def reset_hidden_state(self, env_id: str) -> None:
        if self.spec.algo_type == "lstm":
            self.actor.reset_hidden_state(env_id)

    def select_action(self, state: np.ndarray, prev_state: np.ndarray, prev_action: np.ndarray, env_id: str) -> np.ndarray:
        with torch.no_grad():
            if self.spec.algo_type == "lstm":
                prev_state_t = torch.as_tensor(prev_state[np.newaxis, ...], dtype=torch.float32, device=self.device)
                prev_action_t = torch.as_tensor(prev_action[np.newaxis, ...], dtype=torch.float32, device=self.device)
                current_state_t = torch.as_tensor(state[np.newaxis, ...], dtype=torch.float32, device=self.device)
                prev_state_t = self.normalizer.normalize(prev_state_t)
                current_state_t = self.normalizer.normalize(current_state_t)
                action, _ = self.actor(
                    current_state=current_state_t,
                    deterministic=True,
                    with_logprob=False,
                    env_ids=[env_id],
                    single_step_mode=True,
                    prev_state=prev_state_t,
                    prev_action=prev_action_t,
                )
            else:
                state_t = torch.as_tensor(state[np.newaxis, ...], dtype=torch.float32, device=self.device)
                state_t = self.normalizer.normalize(state_t)
                action, _ = self.actor(current_state=state_t, deterministic=True, with_logprob=False)

        return action.cpu().numpy()[0]

    def adapt_action(self, normalized_action: np.ndarray) -> np.ndarray:
        return self.action_adapter(normalized_action, self.max_action)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on", "enabled"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_workers = max(1, min(8, os.cpu_count() or 1))
    parser = argparse.ArgumentParser(description="Batch evaluate seed-ablation SAC/SAC-LSTM checkpoints")
    parser.add_argument("--config", type=str, default=str(SCRIPT_DIR / "seed_eval_models.csv"))
    parser.add_argument("--model_dir", type=str, default=str(DEFAULT_MODEL_DIR))
    parser.add_argument("--output_dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run_name", type=str, default=None)
    parser.add_argument("--models", type=str, default="all", help="all, or comma-separated model_id/model_family values")
    parser.add_argument("--random_episodes", type=int, default=1000)
    parser.add_argument("--fixed_wind_degs", type=str, default="0,90,150,180")
    parser.add_argument("--fixed_episodes", type=int, default=200)
    parser.add_argument("--max_steps", type=int, default=1000)
    parser.add_argument("--num_workers", type=int, default=default_workers)
    parser.add_argument("--dvc", type=str, default="cpu")
    parser.add_argument("--enable_sensor_noise", type=parse_bool, default=True)
    parser.add_argument("--enable_actuator_noise", type=parse_bool, default=True)
    parser.add_argument("--sensor_noise_ratio", type=float, default=0.03)
    parser.add_argument("--actuator_noise_ratio", type=float, default=0.03)
    parser.add_argument("--dry_run", action="store_true")
    return parser.parse_args(argv)


def resolve_path(path_arg: str, base: Path = REPO_ROOT) -> Path:
    path = Path(path_arg)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def load_model_specs(config_path: Path) -> list[ModelSpec]:
    specs: list[ModelSpec] = []
    with open(config_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            specs.append(
                ModelSpec(
                    enabled=parse_bool(row.get("enabled", "1")),
                    model_id=str(row["model_id"]).strip(),
                    model_family=str(row["model_family"]).strip(),
                    algo_type=str(row["algo_type"]).strip().lower(),
                    env_name=str(row["env_name"]).strip(),
                    model_prefix=str(row["model_prefix"]).strip(),
                    model_step=int(row["model_step"]),
                    net_width=int(row["net_width"]),
                    noise_type=str(row["noise_type"]).strip().lower(),
                    eval_seed=int(row["eval_seed"]),
                )
            )
    return specs


def filter_model_specs(specs: list[ModelSpec], selector: str) -> list[ModelSpec]:
    enabled_specs = [spec for spec in specs if spec.enabled]
    selector = selector.strip()
    if selector.lower() == "all":
        return enabled_specs

    wanted = {item.strip() for item in selector.split(",") if item.strip()}
    selected = [
        spec
        for spec in enabled_specs
        if spec.model_id in wanted or spec.model_family in wanted or spec.model_prefix in wanted
    ]
    if not selected:
        raise ValueError(f"No enabled models matched --models={selector!r}")
    return selected


def parse_fixed_wind_degs(text: str) -> list[float]:
    if not text.strip():
        return []
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def wind_label(deg: float) -> str:
    if float(deg).is_integer():
        return str(int(deg))
    return str(deg).replace(".", "p")


def build_scenarios(args: argparse.Namespace) -> list[ScenarioSpec]:
    scenarios: list[ScenarioSpec] = []
    if args.random_episodes > 0:
        scenarios.append(
            ScenarioSpec(
                scenario="random_wind",
                scenario_group="random_wind",
                target_wind_deg=None,
                num_episodes=args.random_episodes,
                seed_offset=0,
            )
        )

    for idx, deg in enumerate(parse_fixed_wind_degs(args.fixed_wind_degs), start=1):
        if args.fixed_episodes <= 0:
            continue
        scenarios.append(
            ScenarioSpec(
                scenario=f"fixed_wind_{wind_label(deg)}",
                scenario_group="fixed_wind",
                target_wind_deg=float(deg),
                num_episodes=args.fixed_episodes,
                seed_offset=idx * 1_000_000,
            )
        )
    return scenarios


def checkpoint_paths(model_dir: Path, spec: ModelSpec) -> dict[str, Path]:
    return {
        "actor": model_dir / f"{spec.model_prefix}_actor{spec.model_step}.pth",
        "q_critic": model_dir / f"{spec.model_prefix}_q_critic{spec.model_step}.pth",
        "normalizer": model_dir / f"{spec.model_prefix}_normalizer{spec.model_step}.pth",
    }


def validate_checkpoints(model_dir: Path, specs: list[ModelSpec]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for spec in specs:
        paths = checkpoint_paths(model_dir, spec)
        record = {
            "model_id": spec.model_id,
            "model_prefix": spec.model_prefix,
            "model_step": spec.model_step,
            "actor_path": str(paths["actor"]),
            "q_critic_path": str(paths["q_critic"]),
            "normalizer_path": str(paths["normalizer"]),
        }
        for key, path in paths.items():
            exists = path.exists()
            record[f"{key}_exists"] = exists
            record[f"{key}_bytes"] = path.stat().st_size if exists else 0
            if not exists:
                missing.append(f"{spec.model_id}: missing {key} checkpoint: {path}")
        records.append(record)
    if missing:
        raise FileNotFoundError("\n".join(missing))
    return records


def choose_device(dvc: str) -> torch.device:
    if dvc.startswith("cuda") and torch.cuda.is_available():
        return torch.device(dvc)
    return torch.device("cpu")


def make_noise_manager(noise_type: str, sensor_ratio: float, actuator_ratio: float, sensor_enabled: bool, actuator_enabled: bool, seed: int):
    if noise_type == "wind":
        from sailboat_rl.noise_utils_wind import NoiseManager
    elif noise_type == "nowind":
        from sailboat_rl.noise_utils_nowind import NoiseManager
    else:
        raise ValueError(f"Unsupported noise_type: {noise_type}")

    return NoiseManager(
        sensor_noise_ratio=sensor_ratio,
        actuator_noise_ratio=actuator_ratio,
        enable_sensor_noise=sensor_enabled,
        enable_actuator_noise=actuator_enabled,
        seed=seed,
    )


def normalize_angle_rad(angle: float) -> float:
    return float((angle + math.pi) % (2.0 * math.pi) - math.pi)


def angle_to_deg_0_360(angle_rad: float) -> float:
    return float((math.degrees(angle_rad) + 360.0) % 360.0)


def apply_fixed_initial_wind(env, wind_deg: float) -> float:
    wind_rad = math.radians(float(wind_deg))
    unwrapped = getattr(env, "unwrapped", env)

    globals.w0[1] = wind_rad
    globals.w_ini_d = wind_rad
    globals.w_last_d = wind_rad
    globals.w_change_d = wind_rad

    if getattr(unwrapped, "state", None) is not None and len(unwrapped.state) >= 16:
        unwrapped.state[14] = globals.w_change_v
        unwrapped.state[15] = wind_rad
        globals.state = np.copy(unwrapped.state)

    return wind_rad


def seed_episode(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)


def target_xy(obs: np.ndarray) -> tuple[float, float]:
    if len(obs) < 14:
        return (float("nan"), float("nan"))
    return (float(obs[12]), float(obs[13]))


def final_distance(obs: np.ndarray) -> float:
    tx, ty = target_xy(obs)
    if not np.isfinite(tx) or not np.isfinite(ty):
        return float("nan")
    return float(math.hypot(float(obs[0]) - tx, float(obs[1]) - ty))


def action_loop_episode(task: WorkerTask, policy: EvalPolicy, env, scenario: ScenarioSpec, episode_id: int) -> dict[str, Any]:
    run_seed = task.model.eval_seed + scenario.seed_offset + episode_id - 1
    seed_episode(run_seed)

    obs_raw, _ = env.reset(seed=run_seed)
    obs_raw = np.asarray(obs_raw, dtype=np.float32)

    target_wind_deg = scenario.target_wind_deg
    if target_wind_deg is not None:
        initial_wind_rad = apply_fixed_initial_wind(env, target_wind_deg)
        obs_raw = np.asarray(getattr(env.unwrapped, "state", obs_raw), dtype=np.float32).copy()
    else:
        initial_wind_rad = float(globals.w_ini_d)

    initial_heading_rad = float(obs_raw[3]) if len(obs_raw) > 3 else float("nan")
    initial_wind_deg_actual = angle_to_deg_0_360(initial_wind_rad)
    target_x, target_y = target_xy(obs_raw)

    noise_manager = make_noise_manager(
        task.model.noise_type,
        task.sensor_noise_ratio,
        task.actuator_noise_ratio,
        task.enable_sensor_noise,
        task.enable_actuator_noise,
        run_seed,
    )

    state = noise_manager.add_observation_noise(obs_raw) if task.enable_sensor_noise else obs_raw.copy()
    prev_state = state.copy()
    prev_action = np.zeros(policy.action_dim, dtype=np.float32)
    env_id = f"{task.model.model_id}_{scenario.scenario}_{episode_id}"
    policy.reset_hidden_state(env_id)

    previous_xy = np.asarray(obs_raw[0:2], dtype=np.float64)
    sail_angles = [float(obs_raw[8]) if len(obs_raw) > 8 else float("nan")]
    rudder_angles = [float(obs_raw[9]) if len(obs_raw) > 9 else float("nan")]

    path_distance_m = 0.0
    total_reward = 0.0
    steps = 0
    terminated = False
    truncated = False

    while steps < task.max_steps:
        normalized_action = policy.select_action(state, prev_state, prev_action, env_id)
        noisy_action = (
            noise_manager.add_action_noise(normalized_action, policy.max_action)
            if task.enable_actuator_noise
            else normalized_action.copy()
        )
        env_action = policy.adapt_action(noisy_action)

        obs_next_raw, reward, terminated, truncated, _info = env.step(env_action)
        obs_next_raw = np.asarray(obs_next_raw, dtype=np.float32)

        next_xy = np.asarray(obs_next_raw[0:2], dtype=np.float64)
        path_distance_m += float(np.linalg.norm(next_xy - previous_xy))
        previous_xy = next_xy

        sail_angles.append(float(obs_next_raw[8]) if len(obs_next_raw) > 8 else float("nan"))
        rudder_angles.append(float(obs_next_raw[9]) if len(obs_next_raw) > 9 else float("nan"))

        total_reward += float(reward)
        steps += 1

        done = bool(terminated or truncated)
        if done:
            obs_raw = obs_next_raw
            break

        state_next = (
            noise_manager.add_observation_noise(obs_next_raw)
            if task.enable_sensor_noise
            else obs_next_raw.copy()
        )
        prev_state = state.copy()
        prev_action = normalized_action.copy()
        state = state_next
        obs_raw = obs_next_raw

    policy.reset_hidden_state(env_id)

    elapsed_time_s = float(steps) * ACTION_SECONDS
    sail_delta_rad = float(np.nansum(np.abs(np.diff(np.asarray(sail_angles, dtype=np.float64)))))
    rudder_delta_rad = float(np.nansum(np.abs(np.diff(np.asarray(rudder_angles, dtype=np.float64)))))
    sail_rate_rad_s = sail_delta_rad / elapsed_time_s if elapsed_time_s > 0 else float("nan")
    rudder_rate_rad_s = rudder_delta_rad / elapsed_time_s if elapsed_time_s > 0 else float("nan")

    dist = final_distance(obs_raw)
    success = int(np.isfinite(dist) and dist <= SUCCESS_DISTANCE_M)

    return {
        "model_id": task.model.model_id,
        "model_family": task.model.model_family,
        "algo_type": task.model.algo_type,
        "env_name": task.model.env_name,
        "model_prefix": task.model.model_prefix,
        "model_step": task.model.model_step,
        "net_width": task.model.net_width,
        "noise_type": task.model.noise_type,
        "scenario": scenario.scenario,
        "scenario_group": scenario.scenario_group,
        "target_wind_deg": target_wind_deg if target_wind_deg is not None else "",
        "episode_id": episode_id,
        "run_seed": run_seed,
        "initial_wind_rad": initial_wind_rad,
        "initial_wind_deg": initial_wind_deg_actual,
        "initial_heading_rad": initial_heading_rad,
        "initial_heading_deg": angle_to_deg_0_360(initial_heading_rad) if np.isfinite(initial_heading_rad) else float("nan"),
        "target_x": target_x,
        "target_y": target_y,
        "success": success,
        "terminated": int(bool(terminated)),
        "truncated": int(bool(truncated)),
        "steps": steps,
        "time_s": elapsed_time_s,
        "path_distance_m": path_distance_m,
        "final_distance_m": dist,
        "sail_total_change_rad": sail_delta_rad,
        "sail_total_change_deg": math.degrees(sail_delta_rad),
        "sail_change_rate_rad_s": sail_rate_rad_s,
        "sail_change_rate_deg_s": math.degrees(sail_rate_rad_s) if np.isfinite(sail_rate_rad_s) else float("nan"),
        "rudder_total_change_rad": rudder_delta_rad,
        "rudder_total_change_deg": math.degrees(rudder_delta_rad),
        "rudder_change_rate_rad_s": rudder_rate_rad_s,
        "rudder_change_rate_deg_s": math.degrees(rudder_rate_rad_s) if np.isfinite(rudder_rate_rad_s) else float("nan"),
        "total_reward": total_reward,
    }


def run_worker(task: WorkerTask) -> list[dict[str, Any]]:
    torch.set_num_threads(1)
    device = choose_device(task.dvc)
    model_dir = Path(task.model_dir)
    env = gym.make(task.model.env_name)
    policy = EvalPolicy(task.model, env, model_dir, device)
    rows = [action_loop_episode(task, policy, env, task.scenario, episode_id) for episode_id in task.episode_ids]
    env.close()
    return rows


def split_episode_ids(num_episodes: int, chunk_count: int, chunk_idx: int) -> tuple[int, ...]:
    return tuple(i for i in range(1, num_episodes + 1) if (i - 1) % chunk_count == chunk_idx)


def build_worker_tasks(
    specs: list[ModelSpec],
    scenarios: list[ScenarioSpec],
    args: argparse.Namespace,
    model_dir: Path,
) -> list[WorkerTask]:
    worker_count = max(1, int(args.num_workers))
    chunks_per_model = max(1, math.ceil(worker_count / max(1, len(specs))))
    tasks: list[WorkerTask] = []
    for model in specs:
        for scenario in scenarios:
            chunk_count = min(chunks_per_model, max(1, scenario.num_episodes))
            for chunk_idx in range(chunk_count):
                episode_ids = split_episode_ids(scenario.num_episodes, chunk_count, chunk_idx)
                if not episode_ids:
                    continue
                tasks.append(
                    WorkerTask(
                        task_id=f"{model.model_id}:{scenario.scenario}:chunk{chunk_idx + 1}of{chunk_count}",
                        model=model,
                        scenario=scenario,
                        episode_ids=episode_ids,
                        model_dir=str(model_dir),
                        max_steps=args.max_steps,
                        dvc=args.dvc,
                        enable_sensor_noise=bool(args.enable_sensor_noise),
                        enable_actuator_noise=bool(args.enable_actuator_noise),
                        sensor_noise_ratio=float(args.sensor_noise_ratio),
                        actuator_noise_ratio=float(args.actuator_noise_ratio),
                    )
                )
    return tasks


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def finite_array(rows: list[dict[str, Any]], metric: str, success_only: bool) -> np.ndarray:
    values = []
    for row in rows:
        if success_only and int(row["success"]) != 1:
            continue
        value = row.get(metric, float("nan"))
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = float("nan")
        if np.isfinite(value):
            values.append(value)
    return np.asarray(values, dtype=np.float64)


def metric_stats(values: np.ndarray) -> dict[str, float]:
    n = int(values.size)
    if n == 0:
        return {
            "count": 0,
            "mean": float("nan"),
            "std": float("nan"),
            "variance": float("nan"),
            "ci95_low": float("nan"),
            "ci95_high": float("nan"),
        }
    mean = float(np.mean(values))
    if n == 1:
        std = 0.0
        variance = 0.0
        ci_low = mean
        ci_high = mean
    else:
        std = float(np.std(values, ddof=1))
        variance = float(np.var(values, ddof=1))
        half_width = WILSON_Z_95 * std / math.sqrt(n)
        ci_low = mean - half_width
        ci_high = mean + half_width
    return {
        "count": n,
        "mean": mean,
        "std": std,
        "variance": variance,
        "ci95_low": ci_low,
        "ci95_high": ci_high,
    }


def success_rate_wilson(successes: int, total: int) -> tuple[float, float, float]:
    if total <= 0:
        return (float("nan"), float("nan"), float("nan"))
    p = successes / total
    z = WILSON_Z_95
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total) / denom
    return (p, max(0.0, center - half), min(1.0, center + half))


def grouped(rows: list[dict[str, Any]], fields: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = tuple(row.get(field, "") for field in fields)
        groups.setdefault(key, []).append(row)
    return groups


def build_summary_rows(rows: list[dict[str, Any]], group_fields: list[str]) -> list[dict[str, Any]]:
    metrics = [
        "time_s",
        "path_distance_m",
        "final_distance_m",
        "sail_change_rate_rad_s",
        "sail_change_rate_deg_s",
        "rudder_change_rate_rad_s",
        "rudder_change_rate_deg_s",
    ]
    summary_rows: list[dict[str, Any]] = []
    for key, group_rows in grouped(rows, group_fields).items():
        row = {field: value for field, value in zip(group_fields, key)}
        exemplar = group_rows[0]
        for field in [
            "model_prefix",
            "model_step",
            "algo_type",
            "env_name",
            "scenario_group",
            "target_wind_deg",
        ]:
            if field not in row and field in exemplar:
                row[field] = exemplar[field]

        total = len(group_rows)
        successes = sum(int(item["success"]) for item in group_rows)
        success_rate, ci_low, ci_high = success_rate_wilson(successes, total)
        row.update(
            {
                "episodes": total,
                "successes": successes,
                "success_rate": success_rate,
                "success_rate_ci95_low": ci_low,
                "success_rate_ci95_high": ci_high,
            }
        )

        for metric in metrics:
            success_values = finite_array(group_rows, metric, success_only=True)
            stats = metric_stats(success_values)
            prefix = f"success_{metric}"
            for stat_name, stat_value in stats.items():
                row[f"{prefix}_{stat_name}"] = stat_value

        all_final_dist = finite_array(group_rows, "final_distance_m", success_only=False)
        final_stats = metric_stats(all_final_dist)
        for stat_name, stat_value in final_stats.items():
            row[f"all_final_distance_m_{stat_name}"] = stat_value

        summary_rows.append(row)

    return sorted(summary_rows, key=lambda item: tuple(str(item.get(field, "")) for field in group_fields))


def build_boxplot_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = [
        "time_s",
        "path_distance_m",
        "final_distance_m",
        "sail_change_rate_rad_s",
        "sail_change_rate_deg_s",
        "rudder_change_rate_rad_s",
        "rudder_change_rate_deg_s",
    ]
    box_rows: list[dict[str, Any]] = []
    for row in rows:
        for metric in metrics:
            value = row.get(metric, float("nan"))
            box_rows.append(
                {
                    "model_family": row["model_family"],
                    "model_id": row["model_id"],
                    "model_prefix": row["model_prefix"],
                    "model_step": row["model_step"],
                    "scenario": row["scenario"],
                    "scenario_group": row["scenario_group"],
                    "target_wind_deg": row["target_wind_deg"],
                    "metric": metric,
                    "value": value,
                    "success": row["success"],
                    "episode_id": row["episode_id"],
                    "run_seed": row["run_seed"],
                }
            )
    return box_rows


def build_manifest(
    args: argparse.Namespace,
    config_path: Path,
    model_dir: Path,
    output_dir: Path,
    specs: list[ModelSpec],
    scenarios: list[ScenarioSpec],
    checkpoint_records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "script": str(Path(__file__).resolve()),
        "config_path": str(config_path),
        "model_dir": str(model_dir),
        "output_dir": str(output_dir),
        "args": vars(args),
        "models": [asdict(spec) for spec in specs],
        "scenarios": [asdict(scenario) for scenario in scenarios],
        "checkpoints": checkpoint_records,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "gymnasium": getattr(gym, "__version__", "unknown"),
        },
        "output_files": [
            "episodes.csv",
            "summary_by_checkpoint_scenario.csv",
            "summary_by_model_family_scenario.csv",
            "boxplot_values.csv",
            "run_manifest.json",
        ],
    }


def print_dry_run(specs: list[ModelSpec], scenarios: list[ScenarioSpec], checkpoint_records: list[dict[str, Any]]) -> None:
    total = sum(scenario.num_episodes for scenario in scenarios) * len(specs)
    print("Dry run OK.")
    print(f"Models: {len(specs)}")
    print(f"Scenarios: {len(scenarios)}")
    print(f"Total planned episodes: {total}")
    for spec in specs:
        print(f"  - {spec.model_id}: prefix={spec.model_prefix}, step={spec.model_step}, env={spec.env_name}")
    for scenario in scenarios:
        print(
            f"  - scenario={scenario.scenario}, episodes={scenario.num_episodes}, "
            f"target_wind_deg={scenario.target_wind_deg}"
        )
    for record in checkpoint_records:
        print(
            f"  - checkpoints {record['model_id']}: "
            f"actor={record['actor_bytes']}B, q={record['q_critic_bytes']}B, "
            f"normalizer={record['normalizer_bytes']}B"
        )


def main() -> None:
    args = parse_args()
    config_path = resolve_path(args.config)
    model_dir = resolve_path(args.model_dir)
    output_root = resolve_path(args.output_dir)

    specs = filter_model_specs(load_model_specs(config_path), args.models)
    scenarios = build_scenarios(args)
    if not scenarios:
        raise ValueError("No evaluation scenarios requested.")

    checkpoint_records = validate_checkpoints(model_dir, specs)
    if args.dry_run:
        print_dry_run(specs, scenarios, checkpoint_records)
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = args.run_name.strip() if args.run_name else f"seed_eval_{timestamp}"
    output_dir = output_root / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = build_worker_tasks(specs, scenarios, args, model_dir)
    total_episodes = sum(len(task.episode_ids) for task in tasks)
    print(f"Output dir: {output_dir}")
    print(f"Models: {len(specs)}, scenarios: {len(scenarios)}, tasks: {len(tasks)}, episodes: {total_episodes}")
    print(
        f"Noise: sensor={bool(args.enable_sensor_noise)}({args.sensor_noise_ratio}), "
        f"actuator={bool(args.enable_actuator_noise)}({args.actuator_noise_ratio})"
    )
    print(f"Workers: {max(1, int(args.num_workers))}, device={args.dvc}")

    rows: list[dict[str, Any]] = []
    if int(args.num_workers) <= 1:
        for index, task in enumerate(tasks, start=1):
            print(f"[{index}/{len(tasks)}] {task.task_id} episodes={len(task.episode_ids)}")
            rows.extend(run_worker(task))
    else:
        with ProcessPoolExecutor(max_workers=max(1, int(args.num_workers))) as executor:
            future_to_task = {executor.submit(run_worker, task): task for task in tasks}
            completed = 0
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                completed += 1
                task_rows = future.result()
                rows.extend(task_rows)
                print(f"[{completed}/{len(tasks)}] done {task.task_id} episodes={len(task_rows)}")

    rows.sort(key=lambda row: (row["model_family"], row["model_id"], row["scenario"], int(row["episode_id"])))

    episode_fields = [
        "model_id",
        "model_family",
        "algo_type",
        "env_name",
        "model_prefix",
        "model_step",
        "net_width",
        "noise_type",
        "scenario",
        "scenario_group",
        "target_wind_deg",
        "episode_id",
        "run_seed",
        "initial_wind_rad",
        "initial_wind_deg",
        "initial_heading_rad",
        "initial_heading_deg",
        "target_x",
        "target_y",
        "success",
        "terminated",
        "truncated",
        "steps",
        "time_s",
        "path_distance_m",
        "final_distance_m",
        "sail_total_change_rad",
        "sail_total_change_deg",
        "sail_change_rate_rad_s",
        "sail_change_rate_deg_s",
        "rudder_total_change_rad",
        "rudder_total_change_deg",
        "rudder_change_rate_rad_s",
        "rudder_change_rate_deg_s",
        "total_reward",
    ]
    write_csv(output_dir / "episodes.csv", rows, episode_fields)

    checkpoint_summary = build_summary_rows(rows, ["model_id", "scenario"])
    write_csv(output_dir / "summary_by_checkpoint_scenario.csv", checkpoint_summary)

    family_summary = build_summary_rows(rows, ["model_family", "scenario"])
    write_csv(output_dir / "summary_by_model_family_scenario.csv", family_summary)

    box_rows = build_boxplot_rows(rows)
    write_csv(output_dir / "boxplot_values.csv", box_rows)

    manifest = build_manifest(args, config_path, model_dir, output_dir, specs, scenarios, checkpoint_records)
    with open(output_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("Done.")
    print(f"episodes.csv rows: {len(rows)}")
    print(f"checkpoint summaries: {len(checkpoint_summary)}")
    print(f"family summaries: {len(family_summary)}")


if __name__ == "__main__":
    main()
