"""
State-only SAC-LSTM batch test (5 runs by default) with CSV trajectory export and plotting.

Required plot elements:
- start point
- end point
- full trajectory
- random sampled heading arrows from trajectory
- current wind direction arrow
"""

import os
import csv
import argparse
from datetime import datetime

import numpy as np
import torch
import gymnasium as gym
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import globals
from utils_lstm_state_only import str2bool, Action_adapter
from noise_utils_nowind import NoiseManager
from SAC_lstm_state_only import SAC_lstm_countinuous


def parse_args():
    parser = argparse.ArgumentParser(description="State-only SAC-LSTM 5-run evaluator")
    parser.add_argument("--dvc", type=str, default="cpu", help="Device: cuda or cpu")
    parser.add_argument("--model_prefix", type=str, default="saclstm_state_only_s14nowind")
    parser.add_argument("--model_step", type=int, default=9000)
    parser.add_argument("--env_name", type=str, default="sailboat-s14-nowind")
    parser.add_argument("--num_runs", type=int, default=5)
    parser.add_argument("--max_steps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--render", type=str2bool, default=False)
    parser.add_argument("--net_width", type=int, default=256)

    parser.add_argument("--enable_sensor_noise", type=str2bool, default=False)
    parser.add_argument("--enable_actuator_noise", type=str2bool, default=False)
    parser.add_argument("--sensor_noise_ratio", type=float, default=0.03)
    parser.add_argument("--actuator_noise_ratio", type=float, default=0.03)

    parser.add_argument("--heading_samples", type=int, default=8)
    parser.add_argument("--heading_arrow_scale", type=float, default=3.0)
    parser.add_argument("--wind_arrow_scale", type=float, default=8.0)
    parser.add_argument("--plot_seed", type=int, default=0)
    return parser.parse_args()


def ensure_array(x):
    return np.atleast_1d(x)


def sample_heading_indices(num_points, k, rng):
    if num_points <= 0:
        return np.array([], dtype=int)
    if num_points <= k:
        return np.arange(num_points, dtype=int)

    bounds = np.linspace(0, num_points, k + 1, dtype=int)
    indices = []
    for i in range(k):
        lo = bounds[i]
        hi = max(bounds[i + 1], lo + 1)
        idx = rng.integers(lo, hi)
        indices.append(int(idx))
    return np.array(sorted(set(indices)), dtype=int)


def plot_trajectory_from_csv(
    csv_path,
    output_png_path,
    title,
    heading_samples=8,
    heading_arrow_scale=3.0,
    wind_arrow_scale=8.0,
    plot_seed=0,
):
    data = np.genfromtxt(csv_path, delimiter=",", names=True, dtype=np.float64, encoding="utf-8")
    if data.size == 0:
        return

    if data.ndim == 0:
        # Single-row case
        data = np.array([tuple(data.tolist())], dtype=data.dtype)

    names = set(data.dtype.names or [])
    if not {"x", "y", "psi", "wind_dir"}.issubset(names):
        raise ValueError(f"CSV missing required columns in {csv_path}")

    x = ensure_array(data["x"])
    y = ensure_array(data["y"])
    psi = ensure_array(data["psi"])
    wind_dir = ensure_array(data["wind_dir"])
    steps = ensure_array(data["step"]) if "step" in names else np.arange(len(x))

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.plot(x, y, color="tab:blue", linewidth=1.5, alpha=0.9, label="Trajectory")
    ax.plot(x[0], y[0], "go", markersize=10, label="Start")
    ax.plot(x[-1], y[-1], "rs", markersize=8, label="End")

    if "target_x" in names and "target_y" in names:
        tx = float(ensure_array(data["target_x"])[0])
        ty = float(ensure_array(data["target_y"])[0])
        if np.isfinite(tx) and np.isfinite(ty):
            ax.plot(tx, ty, "r*", markersize=14, label="Target")

    # Random sampled heading arrows (reproducible)
    rng = np.random.default_rng(plot_seed)
    indices = sample_heading_indices(len(x), max(1, heading_samples), rng)
    for idx in indices:
        dx = np.cos(psi[idx]) * heading_arrow_scale
        dy = np.sin(psi[idx]) * heading_arrow_scale
        ax.arrow(
            x[idx],
            y[idx],
            dx,
            dy,
            width=0.05,
            head_width=0.6,
            head_length=0.9,
            color="tab:purple",
            alpha=0.8,
            length_includes_head=True,
        )

    # Current wind direction arrow: use last step's wind_dir
    wd = float(wind_dir[-1])
    xmin, xmax = float(np.min(x)), float(np.max(x))
    ymin, ymax = float(np.min(y)), float(np.max(y))
    xr = max(xmax - xmin, 1e-6)
    yr = max(ymax - ymin, 1e-6)
    anchor_x = xmin + 0.82 * xr
    anchor_y = ymin + 0.9 * yr
    wx = np.cos(wd) * wind_arrow_scale
    wy = np.sin(wd) * wind_arrow_scale
    ax.arrow(
        anchor_x,
        anchor_y,
        wx,
        wy,
        width=0.06,
        head_width=0.8,
        head_length=1.2,
        color="tab:orange",
        alpha=0.9,
        length_includes_head=True,
    )
    ax.text(anchor_x, anchor_y, "Wind", color="tab:orange", fontsize=10, ha="right", va="bottom")

    sc = ax.scatter(x, y, c=steps, s=10, cmap="viridis", alpha=0.5)
    plt.colorbar(sc, ax=ax, label="Step")

    ax.set_title(title)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_png_path, dpi=150)
    plt.close(fig)


def run_once(env, agent, noise_manager, max_action, max_steps, run_seed, run_idx):
    obs_raw, _ = env.reset(seed=run_seed)
    s = noise_manager.add_observation_noise(obs_raw) if noise_manager.enable_sensor_noise else obs_raw.copy()

    eval_env_id = f"eval_run_{run_idx}"
    agent.actor.reset_hidden_state(eval_env_id)

    prev_state = s.copy()
    prev_action = np.zeros(env.action_space.shape[0], dtype=np.float32)

    rows = []
    total_reward = 0.0
    step = 0
    done = False

    while not done and step < max_steps:
        a_norm = agent.select_action(prev_state, prev_action, s, deterministic=True, total_steps=0, env_id=eval_env_id)
        a_noisy = (
            noise_manager.add_action_noise(a_norm, max_action)
            if noise_manager.enable_actuator_noise
            else a_norm.copy()
        )
        a_env = Action_adapter(a_noisy, max_action)

        obs_next_raw, reward, terminated, truncated, _ = env.step(a_env)
        done = bool(terminated or truncated)
        s_next = noise_manager.add_observation_noise(obs_next_raw) if noise_manager.enable_sensor_noise else obs_next_raw.copy()

        target_x = float(obs_raw[12]) if len(obs_raw) >= 14 else np.nan
        target_y = float(obs_raw[13]) if len(obs_raw) >= 14 else np.nan
        psi = float(obs_raw[3]) if len(obs_raw) >= 4 else np.nan
        wind_dir = float(globals.w_change_d)

        rows.append(
            {
                "step": int(step),
                "x": float(obs_raw[0]),
                "y": float(obs_raw[1]),
                "psi": psi,
                "target_x": target_x,
                "target_y": target_y,
                "wind_dir": wind_dir,
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


def save_rows_to_csv(rows, csv_path):
    if not rows:
        return
    fieldnames = [
        "step",
        "x",
        "y",
        "psi",
        "target_x",
        "target_y",
        "wind_dir",
        "reward",
        "done",
        "action_sail_cmd_norm",
        "action_rudder_cmd_norm",
        "action_sail_cmd_env",
        "action_rudder_cmd_env",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(out_dir, records):
    summary_csv = os.path.join(out_dir, "summary.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["run_id", "total_reward", "steps", "final_distance", "success"]
        )
        writer.writeheader()
        writer.writerows(records)

    rewards = np.array([r["total_reward"] for r in records], dtype=np.float64)
    steps = np.array([r["steps"] for r in records], dtype=np.float64)
    dists = np.array([r["final_distance"] for r in records], dtype=np.float64)
    succ = np.array([r["success"] for r in records], dtype=np.float64)

    summary_txt = os.path.join(out_dir, "summary.txt")
    with open(summary_txt, "w", encoding="utf-8") as f:
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_results_state_only",
        f"{opt.model_prefix}_{opt.model_step}_{timestamp}",
    )
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output dir: {out_dir}")

    render_mode = "human" if opt.render else None
    env = gym.make(opt.env_name, render_mode=render_mode) if render_mode else gym.make(opt.env_name)
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
    )
    agent.load(opt.model_prefix, opt.model_step)
    agent.actor.eval()
    print(f"Model loaded: {opt.model_prefix} @ {opt.model_step}")
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

    records = []
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

        csv_path = os.path.join(out_dir, f"run_{run_idx:02d}_trajectory.csv")
        png_path = os.path.join(out_dir, f"run_{run_idx:02d}_trajectory.png")
        save_rows_to_csv(rows, csv_path)
        plot_trajectory_from_csv(
            csv_path=csv_path,
            output_png_path=png_path,
            title=f"Run {run_idx:02d} | Reward={total_reward:.2f}",
            heading_samples=opt.heading_samples,
            heading_arrow_scale=opt.heading_arrow_scale,
            wind_arrow_scale=opt.wind_arrow_scale,
            plot_seed=opt.plot_seed + run_idx,
        )

        record = {
            "run_id": run_idx,
            "total_reward": float(total_reward),
            "steps": int(steps),
            "final_distance": float(final_distance) if np.isfinite(final_distance) else np.nan,
            "success": int(success),
        }
        records.append(record)
        print(
            f"Run {run_idx:02d}: reward={record['total_reward']:.2f}, "
            f"steps={record['steps']}, final_dist={record['final_distance']}, success={record['success']}"
        )

    write_summary(out_dir, records)
    env.close()
    print("Done. CSV and plots saved.")


if __name__ == "__main__":
    main()
