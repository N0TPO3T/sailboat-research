"""
Shared 5-run evaluator for the seed/reward ablation experiments.

This module is used by the three concrete test entrypoints:
- test_saclstm_s14_nowind_5runs.py
- test_sac_s14_nowind_5runs.py
- test_sac_s14_wind_5runs.py
"""

import argparse
import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import gymnasium as gym
import matplotlib
import numpy as np
import torch

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import globals

SUCCESS_DISTANCE = 10.0
COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]


@dataclass(frozen=True)
class EvalConfig:
    description: str
    algo_type: str
    agent_cls: object
    action_adapter: object
    str2bool: object
    noise_manager_cls: object
    default_model_prefix: str
    default_env_name: str
    default_net_width: int
    output_root_name: str
    plot_label: str


def parse_args(config):
    parser = argparse.ArgumentParser(description=config.description)
    parser.add_argument("--dvc", type=str, default="cpu", help="Device: cuda or cpu")
    parser.add_argument("--model_dir", type=str, default="./model", help="Checkpoint directory")
    parser.add_argument("--model_prefix", type=str, default=config.default_model_prefix)
    parser.add_argument("--model_step", type=int, default=None, help="Optional checkpoint step")
    parser.add_argument("--env_name", type=str, default=config.default_env_name)
    parser.add_argument("--num_runs", type=int, default=5)
    parser.add_argument("--max_steps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--render", type=config.str2bool, default=False)
    parser.add_argument("--net_width", type=int, default=config.default_net_width)
    parser.add_argument("--enable_sensor_noise", type=config.str2bool, default=True)
    parser.add_argument("--enable_actuator_noise", type=config.str2bool, default=True)
    parser.add_argument("--sensor_noise_ratio", type=float, default=0.03)
    parser.add_argument("--actuator_noise_ratio", type=float, default=0.03)
    parser.add_argument("--heading_samples", type=int, default=8)
    parser.add_argument("--heading_arrow_scale", type=float, default=3.0)
    return parser.parse_args()


def resolve_model_dir(model_dir_arg):
    model_dir = Path(model_dir_arg)
    if model_dir.is_absolute():
        return model_dir
    return (SCRIPT_DIR / model_dir).resolve()


def find_available_steps(model_dir, model_prefix):
    actor_regex = re.compile(rf"^{re.escape(model_prefix)}_actor(\d+)\.pth$")
    steps = []
    for path in model_dir.glob(f"{model_prefix}_actor*.pth"):
        match = actor_regex.match(path.name)
        if match:
            steps.append(int(match.group(1)))
    return sorted(set(steps))


def select_checkpoint_step(model_dir, model_prefix, requested_step):
    available_steps = find_available_steps(model_dir, model_prefix)
    if not available_steps:
        raise FileNotFoundError(
            f"No actor checkpoints found in {model_dir} with prefix '{model_prefix}'."
        )

    if requested_step is not None:
        actor_path = model_dir / f"{model_prefix}_actor{requested_step}.pth"
        q_path = model_dir / f"{model_prefix}_q_critic{requested_step}.pth"
        if not actor_path.exists():
            raise FileNotFoundError(f"Missing actor checkpoint: {actor_path}")
        if not q_path.exists():
            raise FileNotFoundError(f"Missing q_critic checkpoint: {q_path}")
        return requested_step

    valid_steps = [
        step for step in available_steps
        if (model_dir / f"{model_prefix}_q_critic{step}.pth").exists()
    ]
    if not valid_steps:
        raise FileNotFoundError(
            f"Found actor checkpoints but no matching q_critic checkpoints for '{model_prefix}'."
        )
    return max(valid_steps)


def load_model_with_optional_normalizer(agent, model_dir, model_prefix, model_step, device):
    actor_path = model_dir / f"{model_prefix}_actor{model_step}.pth"
    q_path = model_dir / f"{model_prefix}_q_critic{model_step}.pth"
    normalizer_path = model_dir / f"{model_prefix}_normalizer{model_step}.pth"

    agent.actor.load_state_dict(torch.load(actor_path, map_location=device))
    agent.q_critic.load_state_dict(torch.load(q_path, map_location=device))

    if normalizer_path.exists():
        normalizer_state = torch.load(normalizer_path, map_location=device)
        agent.state_normalizer.load_state_dict(normalizer_state)
    else:
        print(f"Warning: missing normalizer checkpoint: {normalizer_path}")


def sample_heading_indices(num_points, k):
    if num_points <= 0:
        return np.array([], dtype=int)
    if num_points <= k:
        return np.arange(num_points, dtype=int)
    return np.linspace(0, num_points - 1, num=k, dtype=int)


def setup_plot_style():
    plt.rcParams["font.sans-serif"] = [
        "SimHei", "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"


def compute_axis_limits(all_run_rows, pad_ratio=0.06):
    xs, ys = [], []
    for rows in all_run_rows:
        if not rows:
            continue
        xs.extend(float(r["x"]) for r in rows)
        ys.extend(float(r["y"]) for r in rows)
        tx = float(rows[0]["target_x"])
        ty = float(rows[0]["target_y"])
        if np.isfinite(tx) and np.isfinite(ty):
            xs.append(tx)
            ys.append(ty)
    if not xs or not ys:
        return None, None
    x_min, x_max = float(np.min(xs)), float(np.max(xs))
    y_min, y_max = float(np.min(ys)), float(np.max(ys))
    x_span = max(x_max - x_min, 1.0)
    y_span = max(y_max - y_min, 1.0)
    return (
        (x_min - x_span * pad_ratio, x_max + x_span * pad_ratio),
        (y_min - y_span * pad_ratio, y_max + y_span * pad_ratio),
    )


def save_rows_to_csv(rows, csv_path):
    if not rows:
        return
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_single_run(rows, output_png, title, plot_label, heading_samples, heading_arrow_scale, xlim, ylim):
    if not rows:
        return

    setup_plot_style()
    x = np.array([r["x"] for r in rows], dtype=float)
    y = np.array([r["y"] for r in rows], dtype=float)
    psi = np.array([r["psi"] for r in rows], dtype=float)
    target_x = float(rows[0]["target_x"])
    target_y = float(rows[0]["target_y"])

    fig, ax = plt.subplots(figsize=(10, 8), dpi=140)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.plot(x, y, color="#1f77b4", linewidth=2.2, label=f"{plot_label} trajectory")
    ax.scatter(x[0], y[0], color="#2ca02c", s=90, edgecolors="black", label="Start", zorder=5)
    ax.scatter(x[-1], y[-1], color="#9467bd", s=80, marker="s", edgecolors="black", label="End", zorder=5)

    if np.isfinite(target_x) and np.isfinite(target_y):
        ax.scatter(target_x, target_y, color="#d62728", marker="*", s=230,
                   edgecolors="black", label="Target", zorder=6)
        ax.add_patch(
            plt.Circle((target_x, target_y), SUCCESS_DISTANCE, color="#d62728",
                       fill=False, linestyle="--", linewidth=1.5, label="Success radius 10m")
        )

    heading_ids = sample_heading_indices(len(x), max(1, heading_samples))
    if len(heading_ids) > 0:
        ax.quiver(
            x[heading_ids],
            y[heading_ids],
            np.cos(psi[heading_ids]),
            np.sin(psi[heading_ids]),
            color="#ff7f0e",
            scale=max(1e-6, 28.0 / max(1e-6, heading_arrow_scale / 3.0)),
            width=0.0055,
            label="Heading",
            zorder=4,
        )

    ax.set_title(title)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.axis("equal")
    ax.legend(loc="best", frameon=True)
    fig.tight_layout()
    fig.savefig(output_png)
    plt.close(fig)


def plot_all_runs(all_run_rows, output_png, plot_label, heading_samples, heading_arrow_scale, xlim, ylim):
    if not all_run_rows:
        return

    setup_plot_style()
    fig, ax = plt.subplots(figsize=(10, 8), dpi=140)
    ax.grid(True, linestyle="--", alpha=0.35)
    target_x, target_y = np.nan, np.nan

    for run_idx, rows in enumerate(all_run_rows, start=1):
        if not rows:
            continue
        color = COLORS[(run_idx - 1) % len(COLORS)]
        x = np.array([r["x"] for r in rows], dtype=float)
        y = np.array([r["y"] for r in rows], dtype=float)
        psi = np.array([r["psi"] for r in rows], dtype=float)
        if run_idx == 1:
            target_x = float(rows[0]["target_x"])
            target_y = float(rows[0]["target_y"])

        ax.plot(x, y, color=color, linewidth=2.0, label=f"Run {run_idx:02d}")
        ax.scatter(x[0], y[0], color=color, s=55, edgecolors="black", linewidths=0.6, zorder=5)
        heading_ids = sample_heading_indices(len(x), max(1, heading_samples // 2))
        if len(heading_ids) > 0:
            ax.quiver(
                x[heading_ids],
                y[heading_ids],
                np.cos(psi[heading_ids]),
                np.sin(psi[heading_ids]),
                color=color,
                scale=max(1e-6, 32.0 / max(1e-6, heading_arrow_scale / 3.0)),
                width=0.004,
                alpha=0.7,
                zorder=4,
            )

    if np.isfinite(target_x) and np.isfinite(target_y):
        ax.scatter(target_x, target_y, color="#d62728", marker="*", s=260,
                   edgecolors="black", label="Target", zorder=6)
        ax.add_patch(
            plt.Circle((target_x, target_y), SUCCESS_DISTANCE, color="#d62728",
                       fill=False, linestyle="--", linewidth=1.5, label="Success radius 10m")
        )

    ax.set_title(f"{plot_label} 5-run trajectories")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.axis("equal")
    ax.legend(loc="best", frameon=True)
    fig.tight_layout()
    fig.savefig(output_png)
    plt.close(fig)


def build_row(step, obs_raw, reward, done, a_norm, a_env, init_obs):
    target_x = float(init_obs[12]) if len(init_obs) >= 14 else np.nan
    target_y = float(init_obs[13]) if len(init_obs) >= 14 else np.nan
    return {
        "step": int(step),
        "x": float(obs_raw[0]),
        "y": float(obs_raw[1]),
        "phi": float(obs_raw[2]) if len(obs_raw) > 2 else np.nan,
        "psi": float(obs_raw[3]) if len(obs_raw) > 3 else np.nan,
        "u": float(obs_raw[4]) if len(obs_raw) > 4 else np.nan,
        "v": float(obs_raw[5]) if len(obs_raw) > 5 else np.nan,
        "p": float(obs_raw[6]) if len(obs_raw) > 6 else np.nan,
        "r": float(obs_raw[7]) if len(obs_raw) > 7 else np.nan,
        "sail_angle": float(obs_raw[8]) if len(obs_raw) > 8 else np.nan,
        "rudder_angle": float(obs_raw[9]) if len(obs_raw) > 9 else np.nan,
        "target_x": target_x,
        "target_y": target_y,
        "wind_speed": float(globals.w_change_v),
        "wind_dir": float(globals.w_change_d),
        "reward": float(reward),
        "done": int(done),
        "terminal_point": 0,
        "action_sail_cmd_norm": float(a_norm[0]),
        "action_rudder_cmd_norm": float(a_norm[1]),
        "action_sail_cmd_env": float(a_env[0]),
        "action_rudder_cmd_env": float(a_env[1]),
    }


def build_terminal_row(step, obs_raw, init_obs):
    return {
        "step": int(step),
        "x": float(obs_raw[0]),
        "y": float(obs_raw[1]),
        "phi": float(obs_raw[2]) if len(obs_raw) > 2 else np.nan,
        "psi": float(obs_raw[3]) if len(obs_raw) > 3 else np.nan,
        "u": float(obs_raw[4]) if len(obs_raw) > 4 else np.nan,
        "v": float(obs_raw[5]) if len(obs_raw) > 5 else np.nan,
        "p": float(obs_raw[6]) if len(obs_raw) > 6 else np.nan,
        "r": float(obs_raw[7]) if len(obs_raw) > 7 else np.nan,
        "sail_angle": float(obs_raw[8]) if len(obs_raw) > 8 else np.nan,
        "rudder_angle": float(obs_raw[9]) if len(obs_raw) > 9 else np.nan,
        "target_x": float(init_obs[12]) if len(init_obs) >= 14 else np.nan,
        "target_y": float(init_obs[13]) if len(init_obs) >= 14 else np.nan,
        "wind_speed": float(globals.w_change_v),
        "wind_dir": float(globals.w_change_d),
        "reward": np.nan,
        "done": 1,
        "terminal_point": 1,
        "action_sail_cmd_norm": np.nan,
        "action_rudder_cmd_norm": np.nan,
        "action_sail_cmd_env": np.nan,
        "action_rudder_cmd_env": np.nan,
    }


def select_action(config, agent, s, prev_state, prev_action, env_id):
    if config.algo_type == "lstm":
        return agent.select_action(
            prev_state,
            prev_action,
            s,
            deterministic=True,
            total_steps=0,
            env_id=env_id,
        )
    return agent.select_action(s, deterministic=True)


def run_once(config, env, agent, opt, max_action, run_seed, run_idx):
    obs_raw, _ = env.reset(seed=run_seed)
    init_obs = obs_raw.copy()

    noise_manager = config.noise_manager_cls(
        sensor_noise_ratio=opt.sensor_noise_ratio,
        actuator_noise_ratio=opt.actuator_noise_ratio,
        enable_sensor_noise=opt.enable_sensor_noise,
        enable_actuator_noise=opt.enable_actuator_noise,
        seed=run_seed,
    )

    s = noise_manager.add_observation_noise(obs_raw) if opt.enable_sensor_noise else obs_raw.copy()
    prev_state = s.copy()
    prev_action = np.zeros(env.action_space.shape[0], dtype=np.float32)
    env_id = f"eval_run_{run_idx}"
    if config.algo_type == "lstm":
        agent.actor.reset_hidden_state(env_id)

    rows = []
    total_reward = 0.0
    step = 0
    done = False

    while not done and step < opt.max_steps:
        a_norm = select_action(config, agent, s, prev_state, prev_action, env_id)
        a_noisy = (
            noise_manager.add_action_noise(a_norm, max_action)
            if opt.enable_actuator_noise
            else a_norm.copy()
        )
        a_env = config.action_adapter(a_noisy, max_action)

        obs_next_raw, reward, terminated, truncated, _ = env.step(a_env)
        done = bool(terminated or truncated)
        s_next = (
            noise_manager.add_observation_noise(obs_next_raw)
            if opt.enable_sensor_noise
            else obs_next_raw.copy()
        )

        rows.append(build_row(step, obs_raw, reward, done, a_norm, a_env, init_obs))

        total_reward += float(reward)
        step += 1
        prev_state = s.copy()
        prev_action = a_norm.copy()
        s = s_next
        obs_raw = obs_next_raw

    rows.append(build_terminal_row(step, obs_raw, init_obs))

    final_distance = np.nan
    success = 0
    if len(obs_raw) >= 14:
        final_distance = float(
            np.sqrt((obs_raw[0] - obs_raw[12]) ** 2 + (obs_raw[1] - obs_raw[13]) ** 2)
        )
        success = int(final_distance <= SUCCESS_DISTANCE)

    mean_reward = float(total_reward / max(step, 1))
    return rows, total_reward, mean_reward, step, final_distance, success


def write_summary(out_dir, records):
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "run_id", "total_reward", "mean_reward", "steps", "final_distance", "success"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    total_rewards = np.array([r["total_reward"] for r in records], dtype=float)
    mean_rewards = np.array([r["mean_reward"] for r in records], dtype=float)
    steps = np.array([r["steps"] for r in records], dtype=float)
    dists = np.array([r["final_distance"] for r in records], dtype=float)
    successes = np.array([r["success"] for r in records], dtype=float)

    with open(out_dir / "summary.txt", "w", encoding="utf-8") as f:
        f.write(f"runs: {len(records)}\n")
        f.write(f"success_rate: {np.mean(successes) * 100.0:.2f}%\n")
        f.write(f"mean_total_reward: {np.mean(total_rewards):.4f}\n")
        f.write(f"std_total_reward: {np.std(total_rewards):.4f}\n")
        f.write(f"mean_step_reward: {np.mean(mean_rewards):.6f}\n")
        f.write(f"std_step_reward: {np.std(mean_rewards):.6f}\n")
        f.write(f"mean_steps: {np.mean(steps):.2f}\n")
        f.write(f"std_steps: {np.std(steps):.2f}\n")
        if np.any(np.isfinite(dists)):
            f.write(f"mean_final_distance: {np.nanmean(dists):.4f}\n")
            f.write(f"std_final_distance: {np.nanstd(dists):.4f}\n")


def main(config):
    opt = parse_args(config)
    model_dir = resolve_model_dir(opt.model_dir)
    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    selected_step = select_checkpoint_step(model_dir, opt.model_prefix, opt.model_step)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = SCRIPT_DIR / config.output_root_name / f"{opt.model_prefix}_{selected_step}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    render_mode = "human" if opt.render else None
    env = gym.make(opt.env_name, render_mode=render_mode) if render_mode else gym.make(opt.env_name)
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    max_action = env.action_space.high.astype(float)

    device = torch.device(opt.dvc if torch.cuda.is_available() else "cpu")
    agent = config.agent_cls(
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
    )
    load_model_with_optional_normalizer(agent, model_dir, opt.model_prefix, selected_step, device)
    agent.actor.eval()

    torch.manual_seed(opt.seed)
    np.random.seed(opt.seed)

    print(f"Output dir: {out_dir}")
    print(f"Model: prefix={opt.model_prefix}, step={selected_step}, model_dir={model_dir}")
    print(f"Env: {opt.env_name}, state_dim={state_dim}, action_dim={action_dim}")
    print(f"Runs: {opt.num_runs}, max_steps={opt.max_steps}, base_seed={opt.seed}")
    print(
        f"Noise: sensor={opt.enable_sensor_noise}({opt.sensor_noise_ratio * 100:.1f}%), "
        f"actuator={opt.enable_actuator_noise}({opt.actuator_noise_ratio * 100:.1f}%)"
    )

    records = []
    all_run_rows = []

    for run_idx in range(1, opt.num_runs + 1):
        run_seed = opt.seed + run_idx - 1
        rows, total_reward, mean_reward, steps, final_distance, success = run_once(
            config=config,
            env=env,
            agent=agent,
            opt=opt,
            max_action=max_action,
            run_seed=run_seed,
            run_idx=run_idx,
        )
        save_rows_to_csv(rows, out_dir / f"run_{run_idx:02d}_trajectory.csv")

        record = {
            "run_id": run_idx,
            "total_reward": float(total_reward),
            "mean_reward": float(mean_reward),
            "steps": int(steps),
            "final_distance": float(final_distance) if np.isfinite(final_distance) else np.nan,
            "success": int(success),
        }
        records.append(record)
        all_run_rows.append(rows)
        print(
            f"Run {run_idx:02d}: total_reward={total_reward:.2f}, "
            f"mean_reward={mean_reward:.4f}, steps={steps}, "
            f"final_distance={record['final_distance']:.2f}, success={success}"
        )

    write_summary(out_dir, records)
    xlim, ylim = compute_axis_limits(all_run_rows)

    for run_idx, rows in enumerate(all_run_rows, start=1):
        record = records[run_idx - 1]
        plot_single_run(
            rows=rows,
            output_png=out_dir / f"run_{run_idx:02d}_trajectory.png",
            title=(
                f"Run {run_idx:02d} | total={record['total_reward']:.2f}, "
                f"mean={record['mean_reward']:.4f}, success={record['success']}"
            ),
            plot_label=config.plot_label,
            heading_samples=opt.heading_samples,
            heading_arrow_scale=opt.heading_arrow_scale,
            xlim=xlim,
            ylim=ylim,
        )

    plot_all_runs(
        all_run_rows=all_run_rows,
        output_png=out_dir / "all_runs_trajectory.png",
        plot_label=config.plot_label,
        heading_samples=opt.heading_samples,
        heading_arrow_scale=opt.heading_arrow_scale,
        xlim=xlim,
        ylim=ylim,
    )

    env.close()
    print("Done. Summary, per-run trajectory CSV files, and trajectory plots saved.")
