"""
SAC-LSTM 5-run evaluator for the local reward ablation environment.

Features:
- Auto scan model directory for actor checkpoints.
- Optional manual --model_step selection.
- Non-strict normalizer loading: warn if missing and continue.
- Run multiple simulations (default 5), save per-run CSV and trajectory plots.
- Save summary_rewards.csv + summary.txt + all_runs_trajectory.png.
"""

import os
import re
import csv
import copy
import argparse
from datetime import datetime
from pathlib import Path

# Keep consistent with existing training/eval scripts to bypass duplicated OpenMP runtime issues.
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import torch
import gymnasium as gym
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import globals
from utils_lstm import str2bool, Action_adapter
from noise_utils_nowind import NoiseManager
from SAC_lstm import SAC_lstm_countinuous
from reward_env import Sailboat_nowind_last

# Colorblind-safe, publication-friendly palette (Wong 2011 style).
JOURNAL_COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
FIG_SIZE = (10, 8)
FIG_DPI = 120


def setup_plot_style():
    # Match the reference plotting style.
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"


def parse_args():
    parser = argparse.ArgumentParser(description="SAC-LSTM 5-run evaluation script")
    parser.add_argument("--dvc", type=str, default="cpu", help="Device: cuda or cpu")
    parser.add_argument("--model_dir", type=str, default="./model_buf1e6", help="Checkpoint directory")
    parser.add_argument("--model_prefix", type=str, default="saclstm_no_dense_progress_speed_s14nowind")
    parser.add_argument("--model_step", type=int, default=None, help="Optional specific checkpoint step")
    parser.add_argument("--env_name", type=str, default="local-no-dense-progress-speed")
    parser.add_argument("--num_runs", type=int, default=5)
    parser.add_argument("--max_steps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--render", type=str2bool, default=False)
    parser.add_argument("--net_width", type=int, default=256)

    parser.add_argument("--enable_sensor_noise", type=str2bool, default=True)
    parser.add_argument("--enable_actuator_noise", type=str2bool, default=True)
    parser.add_argument("--sensor_noise_ratio", type=float, default=0.03)
    parser.add_argument("--actuator_noise_ratio", type=float, default=0.03)

    parser.add_argument("--heading_samples", type=int, default=8)
    parser.add_argument("--heading_arrow_scale", type=float, default=3.0)
    parser.add_argument("--wind_arrow_scale", type=float, default=8.0)
    return parser.parse_args()


def resolve_model_dir(model_dir_arg: str) -> Path:
    p = Path(model_dir_arg)
    if p.is_absolute():
        return p
    return (Path(__file__).resolve().parent / p).resolve()


def find_available_steps(model_dir: Path, model_prefix: str):
    actor_regex = re.compile(rf"^{re.escape(model_prefix)}_actor(\d+)\.pth$")
    steps = []
    for f in model_dir.glob(f"{model_prefix}_actor*.pth"):
        m = actor_regex.match(f.name)
        if m:
            steps.append(int(m.group(1)))
    return sorted(set(steps))


def select_checkpoint_step(model_dir: Path, model_prefix: str, requested_step: int | None):
    available_steps = find_available_steps(model_dir, model_prefix)
    if not available_steps:
        raise FileNotFoundError(
            f"No actor checkpoints found in {model_dir} with prefix '{model_prefix}'."
        )

    if requested_step is not None:
        step = requested_step
        actor_path = model_dir / f"{model_prefix}_actor{step}.pth"
        q_path = model_dir / f"{model_prefix}_q_critic{step}.pth"
        if not actor_path.exists():
            raise FileNotFoundError(f"Missing actor checkpoint: {actor_path}")
        if not q_path.exists():
            raise FileNotFoundError(f"Missing q_critic checkpoint: {q_path}")
        return step

    valid_steps = []
    for step in available_steps:
        q_path = model_dir / f"{model_prefix}_q_critic{step}.pth"
        if q_path.exists():
            valid_steps.append(step)
    if not valid_steps:
        raise FileNotFoundError(
            f"Found actor checkpoints but no matching q_critic checkpoints for prefix '{model_prefix}'."
        )
    return max(valid_steps)


def load_model_with_optional_normalizer(agent, model_dir: Path, model_prefix: str, model_step: int, device):
    actor_path = model_dir / f"{model_prefix}_actor{model_step}.pth"
    q_path = model_dir / f"{model_prefix}_q_critic{model_step}.pth"
    normalizer_path = model_dir / f"{model_prefix}_normalizer{model_step}.pth"

    agent.actor.load_state_dict(torch.load(actor_path, map_location=device))
    agent.q_critic.load_state_dict(torch.load(q_path, map_location=device))

    if normalizer_path.exists():
        normalizer_state = torch.load(normalizer_path, map_location=device)
        agent.state_normalizer.load_state_dict(normalizer_state)
    else:
        print(
            f"Warning: normalizer checkpoint missing for step={model_step}: "
            f"{normalizer_path}. Continue with default normalizer."
        )


def sample_heading_indices(num_points: int, k: int):
    if num_points <= 0:
        return np.array([], dtype=int)
    if num_points <= k:
        return np.arange(num_points, dtype=int)
    return np.linspace(0, num_points - 1, num=k, dtype=int)


def circular_mean_angle(angles_rad: np.ndarray):
    if len(angles_rad) == 0:
        return 0.0
    return float(np.arctan2(np.mean(np.sin(angles_rad)), np.mean(np.cos(angles_rad))))


def compute_global_axis_limits(all_run_rows, pad_ratio=0.06):
    xs = []
    ys = []
    txs = []
    tys = []
    for rows in all_run_rows:
        if not rows:
            continue
        xs.extend([float(r["x"]) for r in rows])
        ys.extend([float(r["y"]) for r in rows])
        tx = float(rows[0]["target_x"])
        ty = float(rows[0]["target_y"])
        if np.isfinite(tx) and np.isfinite(ty):
            txs.append(tx)
            tys.append(ty)

    if txs:
        xs.extend(txs)
        ys.extend(tys)

    if not xs or not ys:
        return None

    x_min = float(np.min(xs))
    x_max = float(np.max(xs))
    y_min = float(np.min(ys))
    y_max = float(np.max(ys))

    x_span = max(x_max - x_min, 1.0)
    y_span = max(y_max - y_min, 1.0)

    x_pad = x_span * pad_ratio
    y_pad = y_span * pad_ratio

    return (x_min - x_pad, x_max + x_pad), (y_min - y_pad, y_max + y_pad)


def make_wind_legend_handle(wind_deg: float):
    # Use an orientation marker (8-direction) to represent real wind direction without numeric angle.
    arrows = ["→", "↗", "↑", "↖", "←", "↙", "↓", "↘"]
    idx = int(((wind_deg % 360.0) + 22.5) // 45) % 8
    arrow_symbol = arrows[idx]
    return Line2D(
        [0],
        [0],
        color="#6B6B6B",
        linewidth=0.0,
        marker=f"${arrow_symbol}$",
        markersize=13,
        label="风向",
    )


def save_rows_to_csv(rows, csv_path: Path):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_single_run(
    rows,
    output_png: Path,
    title: str,
    heading_samples: int,
    heading_arrow_scale: float,
    wind_arrow_scale: float,
    xlim=None,
    ylim=None,
):
    if not rows:
        return

    setup_plot_style()

    x = np.array([r["x"] for r in rows], dtype=float)
    y = np.array([r["y"] for r in rows], dtype=float)
    psi = np.array([r["psi"] for r in rows], dtype=float)
    wind_dir = np.array([r["wind_dir"] for r in rows], dtype=float)
    target_x = float(rows[0]["target_x"])
    target_y = float(rows[0]["target_y"])

    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=FIG_DPI)
    ax.grid(True, linestyle="--", alpha=0.5, zorder=0)

    # 4) Main trajectory line
    line_handle, = ax.plot(
        x, y, color="#1f77b4", linewidth=2.5, label="SAC-LSTM 规划路径", zorder=2
    )

    # 5) Start / target
    start_handle = ax.scatter(
        x[0], y[0], color="#2ca02c", s=120, label="起始点", edgecolors="black", zorder=5
    )
    target_handle = None
    if np.isfinite(target_x) and np.isfinite(target_y):
        target_handle = ax.scatter(
            target_x, target_y, color="#d62728", marker="*", s=250,
            label="目标点", edgecolors="black", zorder=5
        )

    # 6) Heading arrows via quiver (same style as your reference code)
    skip = 40
    if len(x) > 0:
        q = ax.quiver(
            x[::skip],
            y[::skip],
            np.cos(psi[::skip]),
            np.sin(psi[::skip]),
            color="#ff7f0e",
            scale=max(1e-6, 25.0 / max(1e-6, heading_arrow_scale / 3.0)),
            width=0.0065,
            label="船只朝向",
            zorder=3,
        )
    else:
        q = None

    # Wind only in legend
    wind_mean = circular_mean_angle(wind_dir)
    wind_deg = (np.rad2deg(wind_mean) + 360.0) % 360.0
    wind_handle = make_wind_legend_handle(wind_deg)

    ax.set_title("无人帆船自主导航航迹复现（横风）", fontsize=15, pad=15)
    ax.set_xlabel("X 坐标 (m)", fontsize=12)
    ax.set_ylabel("Y 坐标 (m)", fontsize=12)
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.axis("equal")

    legend_handles = [line_handle, start_handle]
    legend_labels = ["SAC-LSTM 规划路径", "起始点"]
    if target_handle is not None:
        legend_handles.append(target_handle)
        legend_labels.append("目标点")
    if q is not None:
        legend_handles.append(q)
        legend_labels.append("船只朝向")
    legend_handles.append(wind_handle)
    legend_labels.append("风向")

    ax.legend(legend_handles, legend_labels, loc="upper right", frameon=True, shadow=True)
    fig.savefig(output_png, dpi=FIG_DPI)
    plt.close(fig)


def plot_all_runs(
    all_run_rows,
    output_png: Path,
    heading_samples: int,
    heading_arrow_scale: float,
    wind_arrow_scale: float,
    xlim=None,
    ylim=None,
):
    if not all_run_rows:
        return

    setup_plot_style()

    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=FIG_DPI)
    ax.grid(True, linestyle="--", alpha=0.5, zorder=0)
    target_x = np.nan
    target_y = np.nan
    run_wind_means = []

    for i, rows in enumerate(all_run_rows, start=1):
        if not rows:
            continue
        color = JOURNAL_COLORS[(i - 1) % len(JOURNAL_COLORS)]
        x = np.array([r["x"] for r in rows], dtype=float)
        y = np.array([r["y"] for r in rows], dtype=float)
        psi = np.array([r["psi"] for r in rows], dtype=float)
        wind_dir = np.array([r["wind_dir"] for r in rows], dtype=float)
        run_wind_means.append((circular_mean_angle(wind_dir), color, i))

        if i == 1:
            target_x = float(rows[0]["target_x"])
            target_y = float(rows[0]["target_y"])

        ax.plot(x, y, linewidth=2.2, alpha=0.95, color=color, label=f"仿真 {i:02d}", zorder=2)
        ax.scatter(x[0], y[0], color=color, s=60, edgecolors="black", linewidths=0.6, zorder=4)

        heading_ids = sample_heading_indices(len(x), max(1, heading_samples // 2))
        if len(heading_ids) > 0:
            ax.quiver(
                x[heading_ids],
                y[heading_ids],
                np.cos(psi[heading_ids]),
                np.sin(psi[heading_ids]),
                color=color,
                scale=max(1e-6, 30.0 / max(1e-6, heading_arrow_scale / 3.0)),
                width=0.0045,
                alpha=0.65,
                zorder=3,
            )

    if np.isfinite(target_x) and np.isfinite(target_y):
        ax.scatter(
            target_x, target_y, s=450, marker="*", color="#d62728",
            edgecolors="#1b1b1b", linewidths=1.3, zorder=7, label="目标点"
        )

    ax.set_title("SAC-LSTM 五次仿真航迹总览（横风）", fontsize=20, pad=14)
    ax.set_xlabel("X 坐标（m）", fontsize=15)
    ax.set_ylabel("Y 坐标（m）", fontsize=15)
    if xlim is not None:
        ax.set_xlim(xlim)
    else:
        ax.set_xlim(-25, 525)
    if ylim is not None:
        ax.set_ylim(ylim)
    else:
        ax.set_ylim(-205, 230)
    ax.axis("equal")
    wind_mean_all = circular_mean_angle(np.array([w for w, _, _ in run_wind_means], dtype=float)) if run_wind_means else 0.0
    wind_deg_all = (np.rad2deg(wind_mean_all) + 360.0) % 360.0
    wind_legend = make_wind_legend_handle(wind_deg_all)
    handles, labels = ax.get_legend_handles_labels()
    handles.append(wind_legend)
    labels.append("风向")
    ax.legend(handles, labels, loc="upper right", frameon=True, fancybox=True, shadow=True, framealpha=0.95, fontsize=11.5)
    fig.savefig(output_png, dpi=FIG_DPI)
    plt.close(fig)


def run_once(env, agent, noise_manager, max_action, max_steps, run_seed, run_idx):
    obs_raw, _ = env.reset(seed=run_seed)
    init_obs = copy.deepcopy(obs_raw)

    s = noise_manager.add_observation_noise(obs_raw) if noise_manager.enable_sensor_noise else obs_raw.copy()
    prev_state = s.copy()
    prev_action = np.zeros(env.action_space.shape[0], dtype=np.float32)

    eval_env_id = f"eval_run_{run_idx}"
    agent.actor.reset_hidden_state(eval_env_id)

    rows = []
    total_reward = 0.0
    step = 0
    done = False

    while not done and step < max_steps:
        a_norm = agent.select_action(
            prev_state,
            prev_action,
            s,
            deterministic=True,
            total_steps=0,
            env_id=eval_env_id,
        )
        a_noisy = (
            noise_manager.add_action_noise(a_norm, max_action)
            if noise_manager.enable_actuator_noise
            else a_norm.copy()
        )
        a_env = Action_adapter(a_noisy, max_action)

        obs_next_raw, reward, terminated, truncated, _ = env.step(a_env)
        done = bool(terminated or truncated)
        s_next = (
            noise_manager.add_observation_noise(obs_next_raw)
            if noise_manager.enable_sensor_noise
            else obs_next_raw.copy()
        )

        target_x = float(init_obs[12]) if len(init_obs) >= 14 else np.nan
        target_y = float(init_obs[13]) if len(init_obs) >= 14 else np.nan

        rows.append(
            {
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
                "action_sail_cmd_norm": float(a_norm[0]),
                "action_rudder_cmd_norm": float(a_norm[1]),
                "action_sail_cmd_env": float(a_env[0]),
                "action_rudder_cmd_env": float(a_env[1]),
            }
        )

        total_reward += float(reward)
        step += 1
        prev_state = s.copy()
        prev_action = a_norm.copy()
        s = s_next
        obs_raw = obs_next_raw

    final_distance = np.nan
    success = 0
    if len(obs_raw) >= 14:
        final_distance = float(np.sqrt((obs_raw[0] - obs_raw[12]) ** 2 + (obs_raw[1] - obs_raw[13]) ** 2))
        success = int(final_distance <= 10.0)

    return rows, total_reward, step, final_distance, success


def write_summary(out_dir: Path, records):
    summary_csv = out_dir / "summary_rewards.csv"
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["run_id", "total_reward", "steps", "final_distance", "success"]
        )
        writer.writeheader()
        writer.writerows(records)

    rewards = np.array([r["total_reward"] for r in records], dtype=float)
    steps = np.array([r["steps"] for r in records], dtype=float)
    dists = np.array([r["final_distance"] for r in records], dtype=float)
    succ = np.array([r["success"] for r in records], dtype=float)

    with open(out_dir / "summary.txt", "w", encoding="utf-8") as f:
        f.write(f"Runs: {len(records)}\n")
        f.write(f"mean_total_reward: {np.mean(rewards):.4f}\n")
        f.write(f"std_total_reward: {np.std(rewards):.4f}\n")
        f.write(f"mean_steps: {np.mean(steps):.2f}\n")
        f.write(f"std_steps: {np.std(steps):.2f}\n")
        if np.any(np.isfinite(dists)):
            f.write(f"mean_final_distance: {np.nanmean(dists):.4f}\n")
            f.write(f"std_final_distance: {np.nanstd(dists):.4f}\n")
        f.write(f"success_rate: {np.mean(succ) * 100.0:.2f}%\n")


def main():
    opt = parse_args()
    model_dir = resolve_model_dir(opt.model_dir)
    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    selected_step = select_checkpoint_step(model_dir, opt.model_prefix, opt.model_step)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).resolve().parent / "test_results_lstm_5runs" / f"{opt.model_prefix}_{selected_step}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {out_dir}")

    render_mode = "human" if opt.render else None
    env = Sailboat_nowind_last(render_mode=render_mode) if render_mode else Sailboat_nowind_last()
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    max_action = env.action_space.high.astype(float)

    device = torch.device(opt.dvc if torch.cuda.is_available() else "cpu")
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
    load_model_with_optional_normalizer(agent, model_dir, opt.model_prefix, selected_step, device)
    agent.actor.eval()

    print(f"Model loaded: prefix={opt.model_prefix}, step={selected_step}, model_dir={model_dir}")
    print(f"Env: {opt.env_name}, runs={opt.num_runs}, max_steps={opt.max_steps}")

    noise_manager = NoiseManager(
        sensor_noise_ratio=opt.sensor_noise_ratio,
        actuator_noise_ratio=opt.actuator_noise_ratio,
        enable_sensor_noise=opt.enable_sensor_noise,
        enable_actuator_noise=opt.enable_actuator_noise,
        seed=opt.seed,
    )
    print(
        f"Noise: sensor={opt.enable_sensor_noise}({opt.sensor_noise_ratio*100:.1f}%), "
        f"actuator={opt.enable_actuator_noise}({opt.actuator_noise_ratio*100:.1f}%)"
    )

    torch.manual_seed(opt.seed)
    np.random.seed(opt.seed)

    records = []
    all_run_rows = []
    run_totals = []

    for run_idx in range(1, opt.num_runs + 1):
        run_seed = opt.seed + run_idx - 1
        rows, total_reward, steps, final_distance, success = run_once(
            env=env,
            agent=agent,
            noise_manager=noise_manager,
            max_action=max_action,
            max_steps=opt.max_steps,
            run_seed=run_seed,
            run_idx=run_idx,
        )

        csv_path = out_dir / f"run_{run_idx:02d}_trajectory.csv"
        save_rows_to_csv(rows, csv_path)

        record = {
            "run_id": run_idx,
            "total_reward": float(total_reward),
            "steps": int(steps),
            "final_distance": float(final_distance) if np.isfinite(final_distance) else np.nan,
            "success": int(success),
        }
        records.append(record)
        all_run_rows.append(rows)
        run_totals.append(float(total_reward))
        print(
            f"Run {run_idx:02d}: reward={record['total_reward']:.2f}, "
            f"steps={record['steps']}, final_dist={record['final_distance']}, success={record['success']}"
        )

    write_summary(out_dir, records)

    global_limits = compute_global_axis_limits(all_run_rows)
    if global_limits is not None:
        xlim, ylim = global_limits
    else:
        xlim, ylim = None, None

    for run_idx, rows in enumerate(all_run_rows, start=1):
        png_path = out_dir / f"run_{run_idx:02d}_trajectory.png"
        plot_single_run(
            rows=rows,
            output_png=png_path,
            title=f"Run {run_idx:02d} | Reward={run_totals[run_idx-1]:.2f}",
            heading_samples=opt.heading_samples,
            heading_arrow_scale=opt.heading_arrow_scale,
            wind_arrow_scale=opt.wind_arrow_scale,
            xlim=xlim,
            ylim=ylim,
        )

    plot_all_runs(
        all_run_rows=all_run_rows,
        output_png=out_dir / "all_runs_trajectory.png",
        heading_samples=opt.heading_samples,
        heading_arrow_scale=opt.heading_arrow_scale,
        wind_arrow_scale=opt.wind_arrow_scale,
        xlim=xlim,
        ylim=ylim,
    )

    env.close()
    print("Done. 5-run CSV files, summary, and trajectory plots saved.")


if __name__ == "__main__":
    main()

