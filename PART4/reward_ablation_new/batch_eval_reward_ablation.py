"""
Batch evaluation for the available SAC-LSTM reward-ablation models.

Each experiment is evaluated in its local s14-nowind reward_env.py. The script
does not plot; it writes per-episode records and summary statistics.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import math
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import gymnasium as gym
import numpy as np
import torch
from stable_baselines3.common.vec_env import SubprocVecEnv


ROOT = Path(__file__).resolve().parent
DEFAULT_EXPERIMENTS = "1,2,3,4"

EXPERIMENTS = [
    {
        "folder": "01_no_dense_progress_speed",
        "label": "no_progress",
        "prefix": "saclstm_no_dense_progress_speed_s14nowind",
    },
    {
        "folder": "02_no_action_penalty",
        "label": "no_action",
        "prefix": "saclstm_no_action_penalty_s14nowind",
    },
    {
        "folder": "03_no_checkpoint",
        "label": "no_checkpoint",
        "prefix": "saclstm_no_checkpoint_s14nowind",
    },
    {
        "folder": "04_no_arrival",
        "label": "no_arrival",
        "prefix": "saclstm_no_arrival_s14nowind",
    },
    {
        "folder": "05_no_penalty",
        "label": "no_penalty",
        "prefix": "saclstm_no_penalty_s14nowind",
    },
]

EPISODE_FIELDS = [
    "experiment",
    "folder",
    "model_prefix",
    "model_step",
    "episode_id",
    "seed",
    "success",
    "steps",
    "time_s",
    "path_distance_m",
    "final_distance_m",
    "sail_total_change_deg",
    "rudder_total_change_deg",
    "sail_change_rate_deg_s",
    "rudder_change_rate_deg_s",
]


class SeededMaxStepWrapper(gym.Wrapper):
    """Seed Python random on every reset and truncate at max_episode_steps."""

    def __init__(self, env, base_seed: int, seed_stride: int, max_episode_steps: int):
        super().__init__(env)
        self.base_seed = int(base_seed)
        self.seed_stride = int(seed_stride)
        self.max_episode_steps = int(max_episode_steps)
        self.episode_index = 0
        self.step_count = 0
        self.current_seed = self.base_seed

    def reset(self, *, seed=None, options=None):
        if seed is None:
            seed = self.base_seed + self.episode_index * self.seed_stride
        seed = int(seed)
        self.current_seed = seed
        self.episode_index += 1
        self.step_count = 0
        random.seed(seed)
        np.random.seed(seed % (2**32 - 1))
        return self.env.reset(seed=seed, options=options)

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        self.step_count += 1
        if self.step_count >= self.max_episode_steps and not terminated:
            truncated = True
        if terminated or truncated:
            info = dict(info)
            info["episode_seed"] = self.current_seed
            info["episode_steps"] = self.step_count
        return obs, reward, terminated, truncated, info


def add_support_path():
    support_dir = ROOT / EXPERIMENTS[0]["folder"]
    support_path = str(support_dir)
    if support_path not in sys.path:
        sys.path.insert(0, support_path)


add_support_path()
from noise_utils_nowind import NoiseManager  # noqa: E402
from SAC_lstm import SAC_lstm_countinuous  # noqa: E402
from utils_lstm import Action_adapter, str2bool  # noqa: E402


def make_env(exp_dir: str, base_seed: int, env_index: int, seed_stride: int, max_steps: int):
    def _init():
        exp_path = str(Path(exp_dir).resolve())
        if exp_path not in sys.path:
            sys.path.insert(0, exp_path)
        for module_name in ("reward_env", "globals"):
            sys.modules.pop(module_name, None)
        reward_env = importlib.import_module("reward_env")
        env = reward_env.Sailboat_nowind_last()
        return SeededMaxStepWrapper(
            env,
            base_seed=base_seed + env_index,
            seed_stride=seed_stride,
            max_episode_steps=max_steps,
        )

    return _init


def parse_args():
    parser = argparse.ArgumentParser(description="Batch evaluate reward-ablation SAC-LSTM models")
    parser.add_argument("--episodes", type=int, default=1000, help="Episodes per experiment")
    parser.add_argument("--num_envs", type=int, default=15, help="Parallel envs per experiment")
    parser.add_argument("--model_step", type=int, default=8400)
    parser.add_argument("--model_dir_name", type=str, default="model")
    parser.add_argument("--max_steps", type=int, default=1000)
    parser.add_argument("--dvc", type=str, default="cpu", help="cpu or cuda")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--experiments",
        type=str,
        default=DEFAULT_EXPERIMENTS,
        help="comma-separated folder names / labels / 1-based indices; use all to include every configured experiment",
    )
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--net_width", type=int, default=256)
    parser.add_argument("--enable_sensor_noise", type=str2bool, default=True)
    parser.add_argument("--enable_actuator_noise", type=str2bool, default=True)
    parser.add_argument("--sensor_noise_ratio", type=float, default=0.03)
    parser.add_argument("--actuator_noise_ratio", type=float, default=0.03)
    parser.add_argument("--progress_interval", type=int, default=50)
    return parser.parse_args()


def select_experiments(selection: str):
    if selection.strip().lower() == "all":
        return EXPERIMENTS

    lookup: dict[str, dict[str, str]] = {}
    for index, exp in enumerate(EXPERIMENTS, start=1):
        lookup[str(index)] = exp
        lookup[exp["folder"]] = exp
        lookup[exp["label"]] = exp

    selected = []
    seen = set()
    for token in [part.strip() for part in selection.split(",") if part.strip()]:
        if token not in lookup:
            valid = ", ".join(exp["folder"] for exp in EXPERIMENTS)
            raise ValueError(f"Unknown experiment '{token}'. Valid: all, 1-5, or {valid}")
        exp = lookup[token]
        if exp["folder"] not in seen:
            selected.append(exp)
            seen.add(exp["folder"])
    if not selected:
        raise ValueError("No experiments selected.")
    return selected


def resolve_output_dir(arg: str | None) -> Path:
    if arg:
        out_dir = Path(arg)
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = ROOT / "test_results_batch" / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir.resolve()


def get_device(device_arg: str):
    requested = device_arg.lower()
    if requested == "cuda" and not torch.cuda.is_available():
        print("Warning: CUDA requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    return torch.device(requested)


def load_model(agent, model_dir: Path, prefix: str, model_step: int, device):
    actor_path = model_dir / f"{prefix}_actor{model_step}.pth"
    q_path = model_dir / f"{prefix}_q_critic{model_step}.pth"
    normalizer_path = model_dir / f"{prefix}_normalizer{model_step}.pth"

    if not actor_path.exists():
        raise FileNotFoundError(f"Missing actor checkpoint: {actor_path}")
    if not q_path.exists():
        raise FileNotFoundError(f"Missing q_critic checkpoint: {q_path}")

    agent.actor.load_state_dict(torch.load(actor_path, map_location=device))
    agent.q_critic.load_state_dict(torch.load(q_path, map_location=device))
    if normalizer_path.exists():
        agent.state_normalizer.load_state_dict(torch.load(normalizer_path, map_location=device))
    else:
        print(f"Warning: missing normalizer checkpoint: {normalizer_path}")


def maybe_noise_obs(noise_manager, obs, enabled: bool):
    if enabled:
        return noise_manager.add_observation_noise(obs)
    return obs.copy()


def run_experiment(exp: dict[str, str], opt, device) -> list[dict[str, Any]]:
    exp_dir = ROOT / exp["folder"]
    model_dir = exp_dir / opt.model_dir_name
    seed_base = opt.seed + EXPERIMENTS.index(exp) * max(opt.episodes * 2, 10000)
    env_fns = [
        make_env(str(exp_dir), seed_base, env_index, opt.num_envs, opt.max_steps)
        for env_index in range(opt.num_envs)
    ]
    vec_env = SubprocVecEnv(env_fns)

    try:
        state_dim = vec_env.observation_space.shape[0]
        action_dim = vec_env.action_space.shape[0]
        max_action = vec_env.action_space.high.astype(float)

        agent = SAC_lstm_countinuous(
            state_dim=state_dim,
            action_dim=action_dim,
            net_width=opt.net_width,
            a_lr=5e-5,
            c_lr=5e-5,
            gamma=0.98,
            batch_size=256,
            alpha=0.2,
            adaptive_alpha=True,
            dvc=device,
            replay_buffer_size=1,
        )
        load_model(agent, model_dir, exp["prefix"], opt.model_step, device)
        agent.actor.eval()
        agent.actor.reset_hidden_state()

        noise_managers = [
            NoiseManager(
                sensor_noise_ratio=opt.sensor_noise_ratio,
                actuator_noise_ratio=opt.actuator_noise_ratio,
                enable_sensor_noise=opt.enable_sensor_noise,
                enable_actuator_noise=opt.enable_actuator_noise,
                seed=seed_base + env_index,
            )
            for env_index in range(opt.num_envs)
        ]

        obs_all = vec_env.reset()
        states = np.array(
            [
                maybe_noise_obs(noise_managers[i], obs_all[i], opt.enable_sensor_noise)
                for i in range(opt.num_envs)
            ]
        )
        prev_states = states.copy()
        prev_actions = np.zeros((opt.num_envs, action_dim), dtype=float)
        prev_raw_obs = obs_all.copy()

        env_steps = np.zeros(opt.num_envs, dtype=int)
        env_path_dist = np.zeros(opt.num_envs, dtype=float)
        env_sail_change = np.zeros(opt.num_envs, dtype=float)
        env_rudder_change = np.zeros(opt.num_envs, dtype=float)

        records: list[dict[str, Any]] = []
        finished = 0
        start = time.perf_counter()

        print(
            f"\n[{exp['folder']}] prefix={exp['prefix']} step={opt.model_step} "
            f"episodes={opt.episodes} num_envs={opt.num_envs}"
        )

        while finished < opt.episodes:
            raw_actions = []
            for i in range(opt.num_envs):
                action = agent.select_action(
                    prev_states[i],
                    prev_actions[i],
                    states[i],
                    deterministic=True,
                    total_steps=0,
                    env_id=i,
                )
                raw_actions.append(action)

            env_actions = []
            for i, action in enumerate(raw_actions):
                if opt.enable_actuator_noise:
                    action = noise_managers[i].add_action_noise(action, max_action)
                env_actions.append(Action_adapter(action, max_action))
            env_actions = np.array(env_actions)

            obs_next_all, _rewards, dones, infos = vec_env.step(env_actions)

            for i in range(opt.num_envs):
                done = bool(dones[i])
                step_obs = infos[i].get("terminal_observation", obs_next_all[i]) if done else obs_next_all[i]

                env_steps[i] += 1
                dx = float(step_obs[0] - prev_raw_obs[i, 0])
                dy = float(step_obs[1] - prev_raw_obs[i, 1])
                env_path_dist[i] += math.sqrt(dx * dx + dy * dy)
                env_sail_change[i] += abs(float(step_obs[8] - prev_raw_obs[i, 8]))
                env_rudder_change[i] += abs(float(step_obs[9] - prev_raw_obs[i, 9]))

                if done and finished < opt.episodes:
                    finished += 1
                    target_x = float(step_obs[12])
                    target_y = float(step_obs[13])
                    final_distance = math.sqrt(
                        float(step_obs[0] - target_x) ** 2 + float(step_obs[1] - target_y) ** 2
                    )
                    success = int(final_distance <= 10.0)
                    time_s = float(env_steps[i])
                    sail_total_deg = float(np.rad2deg(env_sail_change[i]))
                    rudder_total_deg = float(np.rad2deg(env_rudder_change[i]))
                    records.append(
                        {
                            "experiment": exp["label"],
                            "folder": exp["folder"],
                            "model_prefix": exp["prefix"],
                            "model_step": opt.model_step,
                            "episode_id": finished,
                            "seed": infos[i].get("episode_seed", ""),
                            "success": success,
                            "steps": int(env_steps[i]),
                            "time_s": time_s,
                            "path_distance_m": float(env_path_dist[i]),
                            "final_distance_m": float(final_distance),
                            "sail_total_change_deg": sail_total_deg,
                            "rudder_total_change_deg": rudder_total_deg,
                            "sail_change_rate_deg_s": sail_total_deg / time_s if time_s > 0 else np.nan,
                            "rudder_change_rate_deg_s": rudder_total_deg / time_s if time_s > 0 else np.nan,
                        }
                    )

                    if opt.progress_interval > 0 and (
                        finished % opt.progress_interval == 0 or finished == opt.episodes
                    ):
                        elapsed = time.perf_counter() - start
                        print(
                            f"  finished {finished}/{opt.episodes} "
                            f"success={sum(r['success'] for r in records)} elapsed={elapsed:.1f}s"
                        )

                    env_steps[i] = 0
                    env_path_dist[i] = 0.0
                    env_sail_change[i] = 0.0
                    env_rudder_change[i] = 0.0
                    agent.actor.reset_hidden_state(env_id=i)

                if done:
                    reset_noisy = maybe_noise_obs(noise_managers[i], obs_next_all[i], opt.enable_sensor_noise)
                    states[i] = reset_noisy.copy()
                    prev_states[i] = reset_noisy.copy()
                    prev_actions[i] = np.zeros(action_dim, dtype=float)
                    prev_raw_obs[i] = obs_next_all[i].copy()
                else:
                    prev_states[i] = states[i].copy()
                    prev_actions[i] = raw_actions[i].copy()
                    states[i] = maybe_noise_obs(noise_managers[i], obs_next_all[i], opt.enable_sensor_noise)
                    prev_raw_obs[i] = obs_next_all[i].copy()

        return records
    finally:
        vec_env.close()


def wilson_interval(success_count: int, total_count: int, z: float = 1.959963984540054):
    if total_count <= 0:
        return np.nan, np.nan
    phat = success_count / total_count
    z2 = z * z
    denom = 1.0 + z2 / total_count
    center = (phat + z2 / (2.0 * total_count)) / denom
    half = z * math.sqrt((phat * (1.0 - phat) / total_count) + z2 / (4.0 * total_count**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def t_critical_95(df: int) -> float:
    if df <= 0:
        return float("nan")
    try:
        from scipy.stats import t  # type: ignore

        return float(t.ppf(0.975, df))
    except Exception:
        return 1.959963984540054


def continuous_stats(values) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n == 0:
        return {
            "n": 0,
            "mean": np.nan,
            "variance": np.nan,
            "std": np.nan,
            "sem": np.nan,
            "ci95_low": np.nan,
            "ci95_high": np.nan,
        }
    mean = float(np.mean(arr))
    variance = float(np.var(arr, ddof=1)) if n > 1 else 0.0
    std = float(math.sqrt(variance))
    sem = float(std / math.sqrt(n)) if n > 1 else 0.0
    if n > 1:
        half_width = t_critical_95(n - 1) * sem
    else:
        half_width = 0.0
    return {
        "n": n,
        "mean": mean,
        "variance": variance,
        "std": std,
        "sem": sem,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
    }


def add_metric(summary: dict[str, Any], metric_name: str, values):
    stats = continuous_stats(values)
    for key, value in stats.items():
        summary[f"{metric_name}_{key}"] = value


def summarize_records(records: list[dict[str, Any]], selected_experiments, episodes_per_experiment: int):
    summaries = []
    for exp in selected_experiments:
        exp_records = [r for r in records if r["folder"] == exp["folder"]]
        success_records = [r for r in exp_records if int(r["success"]) == 1]
        success_count = len(success_records)
        total_count = len(exp_records)
        ci_low, ci_high = wilson_interval(success_count, total_count)
        success_rate = success_count / total_count if total_count else np.nan
        summary: dict[str, Any] = {
            "experiment": exp["label"],
            "folder": exp["folder"],
            "model_prefix": exp["prefix"],
            "episodes_requested": episodes_per_experiment,
            "episodes_completed": total_count,
            "success_count": success_count,
            "success_rate": success_rate,
            "success_rate_variance": success_rate * (1.0 - success_rate) if total_count else np.nan,
            "success_rate_ci95_low": ci_low,
            "success_rate_ci95_high": ci_high,
        }

        add_metric(summary, "success_time_s", [r["time_s"] for r in success_records])
        add_metric(summary, "success_path_distance_m", [r["path_distance_m"] for r in success_records])
        add_metric(summary, "success_sail_change_rate_deg_s", [r["sail_change_rate_deg_s"] for r in success_records])
        add_metric(summary, "success_rudder_change_rate_deg_s", [r["rudder_change_rate_deg_s"] for r in success_records])
        summaries.append(summary)
    return summaries


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None):
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt_float(value, digits=4):
    try:
        if value is None or not np.isfinite(float(value)):
            return "NA"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "NA"


def write_markdown(path: Path, summaries: list[dict[str, Any]], opt, elapsed_s: float):
    lines = [
        "# Reward Ablation Batch Evaluation",
        "",
        f"- Episodes per experiment: {opt.episodes}",
        f"- Parallel envs: {opt.num_envs}",
        f"- Model step: {opt.model_step}",
        f"- Max steps: {opt.max_steps}",
        f"- Device: {opt.dvc}",
        f"- Sensor noise: {opt.enable_sensor_noise} ({opt.sensor_noise_ratio})",
        f"- Actuator noise: {opt.enable_actuator_noise} ({opt.actuator_noise_ratio})",
        f"- Elapsed seconds: {elapsed_s:.1f}",
        "",
        "| Experiment | Success | Success Rate 95% CI | Time mean s | Distance mean m | Sail rate deg/s | Rudder rate deg/s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summaries:
        lines.append(
            "| {experiment} | {success_count}/{episodes_completed} | {rate} [{ci_l}, {ci_h}] | "
            "{time} | {dist} | {sail} | {rudder} |".format(
                experiment=item["experiment"],
                success_count=item["success_count"],
                episodes_completed=item["episodes_completed"],
                rate=fmt_float(item["success_rate"], 4),
                ci_l=fmt_float(item["success_rate_ci95_low"], 4),
                ci_h=fmt_float(item["success_rate_ci95_high"], 4),
                time=fmt_float(item["success_time_s_mean"], 2),
                dist=fmt_float(item["success_path_distance_m_mean"], 2),
                sail=fmt_float(item["success_sail_change_rate_deg_s_mean"], 4),
                rudder=fmt_float(item["success_rudder_change_rate_deg_s_mean"], 4),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    opt = parse_args()
    selected = select_experiments(opt.experiments)
    output_dir = resolve_output_dir(opt.output_dir)
    device = get_device(opt.dvc)

    print(f"Output dir: {output_dir}")
    print(f"Device: {device}")
    print("Selected experiments:", ", ".join(exp["folder"] for exp in selected))

    torch.manual_seed(opt.seed)
    np.random.seed(opt.seed)
    random.seed(opt.seed)

    all_records: list[dict[str, Any]] = []
    start = time.perf_counter()
    for exp in selected:
        all_records.extend(run_experiment(exp, opt, device))

    summaries = summarize_records(all_records, selected, opt.episodes)
    elapsed = time.perf_counter() - start

    write_csv(output_dir / "episodes.csv", all_records, EPISODE_FIELDS)
    write_csv(output_dir / "summary_by_experiment.csv", summaries)
    write_markdown(output_dir / "summary.md", summaries, opt, elapsed)

    print(f"\nDone. Results written to: {output_dir}")
    print(f"Elapsed: {elapsed:.1f}s")
    for item in summaries:
        print(
            f"{item['experiment']}: success={item['success_count']}/{item['episodes_completed']} "
            f"rate={fmt_float(item['success_rate'] * 100.0, 2)}%"
        )


if __name__ == "__main__":
    main()

