import argparse
import csv
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np


@dataclass
class ModelInput:
    name: str
    k: int
    attention_path: str
    trajectory_path: Optional[str] = None
    episode_index: int = 0


def configure_plot_style() -> None:
    plt.rcParams["font.sans-serif"] = ["SimSun", "Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def _ensure_2d_attention(weights: np.ndarray, model_name: str) -> np.ndarray:
    if weights.ndim != 2:
        raise ValueError(f"[{model_name}] attention 维度必须为2，当前是 {weights.ndim}D")
    if weights.shape[1] <= 1:
        raise ValueError(f"[{model_name}] attention 序列长度太小: {weights.shape}")
    return weights.astype(np.float64)


def load_attention(path: str, model_name: str) -> np.ndarray:
    if not os.path.exists(path):
        raise FileNotFoundError(f"[{model_name}] 找不到注意力文件: {path}")
    weights = np.load(path, allow_pickle=True)
    return _ensure_2d_attention(weights, model_name)


def load_trajectory(path: str, episode_index: int, model_name: str) -> np.ndarray:
    if not os.path.exists(path):
        raise FileNotFoundError(f"[{model_name}] 找不到轨迹文件: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".npy":
        arr = np.load(path, allow_pickle=True)
        if arr.dtype == object:
            if episode_index < 0 or episode_index >= len(arr):
                raise IndexError(
                    f"[{model_name}] episode_index={episode_index} 超出范围 [0, {len(arr)-1}]"
                )
            traj = np.asarray(arr[episode_index], dtype=np.float64)
        else:
            traj = np.asarray(arr, dtype=np.float64)
    else:
        traj = np.loadtxt(path, delimiter=",")

    if traj.ndim != 2 or traj.shape[1] < 2:
        raise ValueError(f"[{model_name}] 轨迹必须至少包含2列(x,y)，当前shape={traj.shape}")
    return traj[:, :2]


def parse_obstacles(raw_obstacles: List[List[float]]) -> np.ndarray:
    obs = np.asarray(raw_obstacles, dtype=np.float64)
    if obs.ndim != 2 or obs.shape[1] != 2:
        raise ValueError("obstacles 必须是 [[x1,y1],[x2,y2],...] 格式")
    return obs


def compute_clearance_profile(traj_xy: np.ndarray, obstacles_xy: np.ndarray) -> np.ndarray:
    diff = traj_xy[:, None, :] - obstacles_xy[None, :, :]
    dist = np.linalg.norm(diff, axis=2)
    return dist.min(axis=1)


def split_semantic_stages(
    clearance: np.ndarray,
    enter_distance: float,
    leave_distance: float,
    sustain_steps: int = 3,
) -> Dict[str, Tuple[int, int]]:
    n = len(clearance)
    if n < 6:
        raise ValueError("轨迹长度过短，无法进行阶段划分")

    i_min = int(np.argmin(clearance))

    enter_candidates = np.where(clearance[: i_min + 1] <= enter_distance)[0]
    if len(enter_candidates) > 0:
        i_enter = int(enter_candidates[0])
    else:
        i_enter = max(0, i_min - max(3, n // 8))

    i_leave = None
    for i in range(i_min, n):
        if clearance[i] >= leave_distance:
            end_check = min(n, i + sustain_steps)
            if np.all(clearance[i:end_check] >= leave_distance):
                i_leave = i
                break
    if i_leave is None:
        i_leave = min(n - 1, i_min + max(3, n // 8))

    i_enter = max(1, min(i_enter, n - 3))
    i_leave = max(i_enter + 1, min(i_leave, n - 1))

    return {
        "approach": (0, i_enter),
        "decision": (i_enter, i_leave),
        "recovery": (i_leave, n),
    }


def split_by_ratio(total_steps: int, ratios: List[float]) -> Dict[str, Tuple[int, int]]:
    ratios = np.asarray(ratios, dtype=np.float64)
    ratios = ratios / ratios.sum()
    b1 = int(total_steps * ratios[0])
    b2 = int(total_steps * (ratios[0] + ratios[1]))
    b1 = max(1, min(b1, total_steps - 2))
    b2 = max(b1 + 1, min(b2, total_steps - 1))
    return {
        "approach": (0, b1),
        "decision": (b1, b2),
        "recovery": (b2, total_steps),
    }


def stage_metrics(stage_weights: np.ndarray, recent_fraction: float) -> Dict[str, float]:
    eps = 1e-10
    t, k = stage_weights.shape
    pos = np.linspace(0.0, 1.0, k)

    entropy = -np.sum(stage_weights * np.log(stage_weights + eps), axis=1)
    entropy_norm = entropy / np.log(k)

    center = np.sum(stage_weights * pos[None, :], axis=1)
    recent_start = max(0, int(np.floor((1.0 - recent_fraction) * k)))
    recent_ratio = stage_weights[:, recent_start:].sum(axis=1)

    return {
        "mean_entropy_norm": float(np.mean(entropy_norm)),
        "std_entropy_norm": float(np.std(entropy_norm)),
        "mean_recency_center": float(np.mean(center)),
        "std_recency_center": float(np.std(center)),
        "mean_recent_ratio": float(np.mean(recent_ratio)),
        "std_recent_ratio": float(np.std(recent_ratio)),
        "num_steps": int(t),
    }


def interpolate_to_common_axis(weights_1d: np.ndarray, bins: int) -> np.ndarray:
    k = len(weights_1d)
    src_x = np.linspace(0.0, 1.0, k)
    dst_x = np.linspace(0.0, 1.0, bins)
    return np.interp(dst_x, src_x, weights_1d)


def ema_smooth(x: np.ndarray, alpha: float) -> np.ndarray:
    if len(x) == 0:
        return x.copy()
    y = np.asarray(x, dtype=np.float64).copy()
    for i in range(1, len(y)):
        y[i] = alpha * y[i] + (1.0 - alpha) * y[i - 1]
    return y


def compute_observation_set_signals(
    traj_xy: np.ndarray,
    obstacles_xy: np.ndarray,
    detection_radius: float,
) -> Tuple[np.ndarray, np.ndarray]:
    n = len(traj_xy)
    pair_ids = np.full((n, 2), -1, dtype=np.int64)
    risk = np.full(n, np.inf, dtype=np.float64)

    for t in range(n):
        dist = np.linalg.norm(obstacles_xy - traj_xy[t][None, :], axis=1)
        valid = np.where(dist <= detection_radius)[0]
        if len(valid) == 0:
            continue

        order = valid[np.argsort(dist[valid])]
        i1 = int(order[0])
        i2 = int(order[1]) if len(order) >= 2 else -1
        pair_ids[t, 0] = i1
        pair_ids[t, 1] = i2

        d1 = dist[i1]
        d2 = dist[i2] if i2 >= 0 else np.inf
        risk[t] = min(d1, d2)

    return pair_ids, risk


def detect_observation_events(
    pair_ids: np.ndarray,
    risk_raw: np.ndarray,
    enter_distance: float,
    leave_distance: float,
    approach_delta: float,
    leave_delta: float,
    sustain_steps: int,
    switch_cooldown: int,
    smoothing_alpha: float,
) -> List[Dict[str, object]]:
    n = len(risk_raw)
    if n < 3:
        return []

    finite = np.isfinite(risk_raw)
    if not np.any(finite):
        return []

    fill_val = max(leave_distance * 1.5, float(np.max(risk_raw[finite])))
    risk_filled = np.where(finite, risk_raw, fill_val)
    risk_smooth = ema_smooth(risk_filled, smoothing_alpha)
    dr = np.diff(risk_smooth, prepend=risk_smooth[0])

    events: List[Dict[str, object]] = []
    last_t = {"switch": -10**9, "approach": -10**9, "leave": -10**9}

    for t in range(1, n):
        switched = not np.array_equal(pair_ids[t], pair_ids[t - 1])
        if switched and (t - last_t["switch"] >= switch_cooldown):
            events.append(
                {
                    "type": "switch",
                    "t": int(t),
                    "pair_prev": pair_ids[t - 1].tolist(),
                    "pair_now": pair_ids[t].tolist(),
                    "risk": float(risk_smooth[t]),
                }
            )
            last_t["switch"] = t

        if t >= sustain_steps - 1:
            w0 = t - sustain_steps + 1
            seg_r = risk_smooth[w0 : t + 1]
            seg_dr = dr[w0 : t + 1]

            if (
                np.all(seg_r <= enter_distance)
                and float(np.mean(seg_dr)) <= -abs(approach_delta)
                and (t - last_t["approach"] >= sustain_steps)
            ):
                events.append(
                    {
                        "type": "approach",
                        "t": int(t),
                        "pair_now": pair_ids[t].tolist(),
                        "risk": float(risk_smooth[t]),
                        "dr_mean": float(np.mean(seg_dr)),
                    }
                )
                last_t["approach"] = t

            if (
                np.all(seg_r >= leave_distance)
                and float(np.mean(seg_dr)) >= abs(leave_delta)
                and (t - last_t["leave"] >= sustain_steps)
            ):
                events.append(
                    {
                        "type": "leave",
                        "t": int(t),
                        "pair_now": pair_ids[t].tolist(),
                        "risk": float(risk_smooth[t]),
                        "dr_mean": float(np.mean(seg_dr)),
                    }
                )
                last_t["leave"] = t

    return events


def extract_event_windows(
    events: List[Dict[str, object]],
    total_steps: int,
    window_left: int,
    window_right: int,
    min_window_len: int,
) -> List[Dict[str, object]]:
    windows: List[Dict[str, object]] = []
    for e in events:
        t = int(e["t"])
        start = max(0, t - window_left)
        end = min(total_steps, t + window_right + 1)
        if end - start < min_window_len:
            continue
        item = dict(e)
        item["start"] = int(start)
        item["end"] = int(end)
        windows.append(item)
    return windows


def save_metrics_csv(path: str, rows: List[Dict[str, object]], mode: str = "stage") -> None:
    if mode == "stage":
        fieldnames = [
            "model",
            "k",
            "stage",
            "num_steps",
            "mean_entropy_norm",
            "std_entropy_norm",
            "mean_recency_center",
            "std_recency_center",
            "mean_recent_ratio",
            "std_recent_ratio",
        ]
    else:
        fieldnames = [
            "model",
            "k",
            "event_type",
            "num_windows",
            "num_steps",
            "mean_entropy_norm",
            "std_entropy_norm",
            "mean_recency_center",
            "std_recency_center",
            "mean_recent_ratio",
            "std_recent_ratio",
        ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_stage_profiles(
    out_path: str,
    stage_profiles: Dict[str, List[Tuple[str, int, np.ndarray]]],
) -> None:
    stages = ["approach", "decision", "recovery"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    x = np.linspace(0.0, 1.0, len(next(iter(stage_profiles.values()))[0][2]))

    for i, stage in enumerate(stages):
        ax = axes[i]
        for model_name, k, profile in stage_profiles[stage]:
            ax.plot(x, profile, linewidth=2, label=f"{model_name} (K={k})")
        ax.set_title(stage)
        ax.set_xlabel("Relative history position (0=oldest, 1=most recent)")
        ax.grid(True, linestyle="--", alpha=0.4)

    axes[0].set_ylabel("Mean attention weight")
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=max(1, len(labels)))
    fig.suptitle("Semantic-stage aligned attention comparison", y=1.06, fontsize=14)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_stage_metrics(out_path: str, metrics_rows: List[Dict[str, object]]) -> None:
    stages = ["approach", "decision", "recovery"]
    models = sorted(list({str(r["model"]) for r in metrics_rows}))

    def build_matrix(metric_name: str) -> np.ndarray:
        mat = np.zeros((len(stages), len(models)), dtype=np.float64)
        for i, s in enumerate(stages):
            for j, m in enumerate(models):
                vals = [float(r[metric_name]) for r in metrics_rows if r["stage"] == s and r["model"] == m]
                mat[i, j] = vals[0] if vals else np.nan
        return mat

    metric_specs = [
        ("mean_entropy_norm", "Entropy (norm)"),
        ("mean_recency_center", "Recency center"),
        ("mean_recent_ratio", "Recent ratio"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
    for ax, (metric_key, title) in zip(axes, metric_specs):
        mat = build_matrix(metric_key)
        im = ax.imshow(mat, aspect="auto", cmap="viridis")
        ax.set_title(title)
        ax.set_xticks(np.arange(len(models)))
        ax.set_xticklabels(models, rotation=20)
        ax.set_yticks(np.arange(len(stages)))
        ax.set_yticklabels(stages)
        for i in range(len(stages)):
            for j in range(len(models)):
                val = mat[i, j]
                if np.isfinite(val):
                    ax.text(j, i, f"{val:.3f}", ha="center", va="center", color="white", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("Stage-wise attention metrics", y=1.02, fontsize=14)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_event_profiles(
    out_path: str,
    event_profiles: Dict[str, List[Tuple[str, int, np.ndarray]]],
) -> None:
    event_types = ["switch", "approach", "leave"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)

    non_empty = [v for v in event_profiles.values() if len(v) > 0]
    if len(non_empty) == 0:
        return
    x = np.linspace(0.0, 1.0, len(non_empty[0][0][2]))

    for i, e in enumerate(event_types):
        ax = axes[i]
        for model_name, k, profile in event_profiles[e]:
            ax.plot(x, profile, linewidth=2, label=f"{model_name} (K={k})")
        ax.set_title(e)
        ax.set_xlabel("Relative history position (0=oldest, 1=most recent)")
        ax.grid(True, linestyle="--", alpha=0.4)

    axes[0].set_ylabel("Mean attention weight (event windows)")
    handles, labels = axes[-1].get_legend_handles_labels()
    if len(labels) > 0:
        fig.legend(handles, labels, loc="upper center", ncol=max(1, len(labels)))
    fig.suptitle("Observation-event aligned attention comparison", y=1.06, fontsize=14)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_single_event_profile(
    out_path: str,
    event_type: str,
    profiles: List[Tuple[str, int, np.ndarray]],
) -> None:
    configure_plot_style()
    fig, ax = plt.subplots(1, 1, figsize=(8.8, 5.2))

    if len(profiles) == 0:
        ax.set_xlabel("相对历史位置（0=最旧，1=最新）", fontname="SimSun", fontsize=12)
        ax.set_ylabel("平均注意力权重", fontname="SimSun", fontsize=12)
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.text(
            0.5,
            0.5,
            f"{event_type} 事件无可用窗口",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=13,
            fontname="SimSun",
        )
        plt.tight_layout()
        plt.savefig(out_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return

    profile_len = len(profiles[0][2])
    x = np.linspace(0.0, 1.0, profile_len)
    colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, max(3, len(profiles))))

    for idx, (model_name, k, profile) in enumerate(profiles):
        mark_step = max(1, profile_len // 8)
        ax.plot(
            x,
            profile,
            linewidth=2.4,
            color=colors[idx],
            marker="o",
            markersize=4,
            markevery=mark_step,
            label=f"{model_name} (K={k})",
        )

    ax.set_xlabel("相对历史位置（0=最旧，1=最新）", fontname="SimSun", fontsize=12)
    ax.set_ylabel("平均注意力权重", fontname="SimSun", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.tick_params(axis="both", labelsize=11)
    ax.legend(
        loc="best",
        fontsize=10,
        frameon=True,
        framealpha=0.95,
        prop={"family": "SimSun", "size": 10},
    )

    plt.tight_layout()
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_event_metrics(out_path: str, metrics_rows: List[Dict[str, object]]) -> None:
    event_types = ["switch", "approach", "leave"]
    models = sorted(list({str(r["model"]) for r in metrics_rows}))

    def build_matrix(metric_name: str) -> np.ndarray:
        mat = np.zeros((len(event_types), len(models)), dtype=np.float64)
        for i, e in enumerate(event_types):
            for j, m in enumerate(models):
                vals = [float(r[metric_name]) for r in metrics_rows if r["event_type"] == e and r["model"] == m]
                mat[i, j] = vals[0] if vals else np.nan
        return mat

    metric_specs = [
        ("mean_entropy_norm", "Entropy (norm)"),
        ("mean_recency_center", "Recency center"),
        ("mean_recent_ratio", "Recent ratio"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
    for ax, (metric_key, title) in zip(axes, metric_specs):
        mat = build_matrix(metric_key)
        im = ax.imshow(mat, aspect="auto", cmap="viridis")
        ax.set_title(title)
        ax.set_xticks(np.arange(len(models)))
        ax.set_xticklabels(models, rotation=20)
        ax.set_yticks(np.arange(len(event_types)))
        ax.set_yticklabels(event_types)
        for i in range(len(event_types)):
            for j in range(len(models)):
                val = mat[i, j]
                if np.isfinite(val):
                    ax.text(j, i, f"{val:.3f}", ha="center", va="center", color="white", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("Event-wise attention metrics", y=1.02, fontsize=14)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_single_event_metrics(
    out_path: str,
    event_type: str,
    metrics_rows: List[Dict[str, object]],
) -> None:
    configure_plot_style()
    metric_specs = [
        ("mean_entropy_norm", "归一化熵"),
        ("mean_recency_center", "近期中心"),
        ("mean_recent_ratio", "近期占比"),
    ]

    event_rows = [r for r in metrics_rows if str(r["event_type"]) == event_type]
    models = sorted(list({str(r["model"]) for r in event_rows}))

    fig, ax = plt.subplots(1, 1, figsize=(8.8, 5.4))

    if len(event_rows) == 0:
        ax.set_xlabel("模型", fontname="SimSun", fontsize=11)
        ax.set_ylabel("指标", fontname="SimSun", fontsize=11)
        ax.text(
            0.5,
            0.5,
            f"{event_type} 事件无可用指标",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
            fontname="SimSun",
        )
        plt.tight_layout()
        plt.savefig(out_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return

    metric_names = [name for _, name in metric_specs]
    mat = np.zeros((len(metric_specs), len(models)), dtype=np.float64)
    for i, (metric_key, _) in enumerate(metric_specs):
        for j, m in enumerate(models):
            vals = [float(r[metric_key]) for r in event_rows if str(r["model"]) == m]
            mat[i, j] = vals[0] if len(vals) > 0 else np.nan

    im = ax.imshow(mat, aspect="auto", cmap="cividis")

    ax.set_xticks(np.arange(len(models)))
    ax.set_xticklabels(models, rotation=18, fontsize=10, fontname="SimSun")
    ax.set_yticks(np.arange(len(metric_names)))
    ax.set_yticklabels(metric_names, fontsize=11, fontname="SimSun")
    ax.set_xlabel("模型", fontname="SimSun", fontsize=11)
    ax.set_ylabel("指标", fontname="SimSun", fontsize=11)

    finite_vals = mat[np.isfinite(mat)]
    if len(finite_vals) > 0:
        threshold = float(np.median(finite_vals))
    else:
        threshold = 0.0

    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            val = mat[i, j]
            if not np.isfinite(val):
                ax.text(j, i, "N/A", ha="center", va="center", fontsize=10, color="black")
                continue
            text_color = "white" if val <= threshold else "black"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center", fontsize=10, color=text_color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_metric_event_model_heatmap(
    out_path: str,
    metrics_rows: List[Dict[str, object]],
    metric_key: str,
    metric_label_cn: str,
) -> None:
    configure_plot_style()
    event_types = ["switch", "approach", "leave"]
    models = sorted(list({str(r["model"]) for r in metrics_rows}))

    fig, ax = plt.subplots(1, 1, figsize=(8.8, 5.4))

    if len(models) == 0:
        ax.set_xlabel("模型", fontname="SimSun", fontsize=11)
        ax.set_ylabel("事件类型", fontname="SimSun", fontsize=11)
        ax.text(
            0.5,
            0.5,
            "无可用指标",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
            fontname="SimSun",
        )
        plt.tight_layout()
        plt.savefig(out_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return

    mat = np.full((len(event_types), len(models)), np.nan, dtype=np.float64)
    for i, event_type in enumerate(event_types):
        for j, model_name in enumerate(models):
            vals = [
                float(r[metric_key])
                for r in metrics_rows
                if str(r.get("event_type", "")) == event_type and str(r.get("model", "")) == model_name
            ]
            if len(vals) > 0:
                mat[i, j] = vals[0]

    im = ax.imshow(mat, aspect="auto", cmap="cividis")
    ax.set_xticks(np.arange(len(models)))
    ax.set_xticklabels(models, rotation=18, fontsize=10, fontname="SimSun")
    ax.set_yticks(np.arange(len(event_types)))
    ax.set_yticklabels(event_types, fontsize=11, fontname="SimSun")
    ax.set_xlabel("模型", fontname="SimSun", fontsize=11)
    ax.set_ylabel("事件类型", fontname="SimSun", fontsize=11)

    finite_vals = mat[np.isfinite(mat)]
    threshold = float(np.median(finite_vals)) if len(finite_vals) > 0 else 0.0

    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            val = mat[i, j]
            if not np.isfinite(val):
                ax.text(j, i, "N/A", ha="center", va="center", fontsize=10, color="black")
            else:
                text_color = "white" if val <= threshold else "black"
                ax.text(j, i, f"{val:.3f}", ha="center", va="center", fontsize=10, color=text_color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(metric_label_cn, fontname="SimSun", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def default_config_template() -> Dict[str, object]:
    return {
        "analysis_mode": "observation_event",
        "models": [
            {
                "name": "K5",
                "k": 5,
                "attention_path": "C:/Users/24809/Desktop/py_RL/attention_weights_k5.npy",
                "trajectory_path": "C:/Users/24809/Desktop/trajectories_k5.npy",
                "episode_index": 0,
            },
            {
                "name": "K10",
                "k": 10,
                "attention_path": "C:/Users/24809/Desktop/py_RL/attention_weights_k10.npy",
                "trajectory_path": "C:/Users/24809/Desktop/trajectories_k10.npy",
                "episode_index": 0,
            },
            {
                "name": "K20",
                "k": 20,
                "attention_path": "C:/Users/24809/Desktop/py_RL/attention_weights_k20.npy",
                "trajectory_path": "C:/Users/24809/Desktop/trajectories_k20.npy",
                "episode_index": 0,
            },
        ],
        "obstacles": [[500.0, 500.0], [800.0, 350.0], [650.0, 420.0], [300.0, 700.0]],
        "detection_radius": 150.0,
        "enter_distance": 120.0,
        "leave_distance": 150.0,
        "approach_delta": 2.0,
        "leave_delta": 2.0,
        "sustain_steps": 3,
        "switch_cooldown": 5,
        "smoothing_alpha": 0.3,
        "event_window_left": 10,
        "event_window_right": 0,
        "event_min_window_len": 4,
        "fallback_ratios": [0.4, 0.3, 0.3],
        "recent_fraction": 0.3,
        "resample_bins": 50,
        "output_dir": "./attn_stage_compare_results",
    }


def parse_models(config: Dict[str, object]) -> List[ModelInput]:
    raw_models = config.get("models", [])
    if not isinstance(raw_models, list) or len(raw_models) == 0:
        raise ValueError("配置中 models 不能为空")

    models: List[ModelInput] = []
    for item in raw_models:
        models.append(
            ModelInput(
                name=str(item["name"]),
                k=int(item["k"]),
                attention_path=str(item["attention_path"]),
                trajectory_path=item.get("trajectory_path"),
                episode_index=int(item.get("episode_index", 0)),
            )
        )
    return models


def run_stage_mode(config: Dict[str, object]) -> None:
    models = parse_models(config)
    output_dir = str(config.get("output_dir", "./attn_stage_compare_results"))
    os.makedirs(output_dir, exist_ok=True)

    fallback_ratios = list(config.get("fallback_ratios", [0.4, 0.3, 0.3]))
    recent_fraction = float(config.get("recent_fraction", 0.3))
    bins = int(config.get("resample_bins", 50))

    raw_obstacles = config.get("obstacles", None)
    obstacles_xy = parse_obstacles(raw_obstacles) if raw_obstacles is not None else None
    enter_distance = float(config.get("enter_distance", 120.0))
    leave_distance = float(config.get("leave_distance", 150.0))

    metrics_rows: List[Dict[str, object]] = []
    stage_profiles: Dict[str, List[Tuple[str, int, np.ndarray]]] = {
        "approach": [],
        "decision": [],
        "recovery": [],
    }
    stage_meta: Dict[str, Dict[str, Tuple[int, int]]] = {}

    for model in models:
        att = load_attention(model.attention_path, model.name)
        seq_len = att.shape[1]
        if model.k != seq_len:
            print(f"[警告] {model.name}: config中的k={model.k}，但attention列数={seq_len}，将使用{seq_len}")

        if model.trajectory_path:
            traj = load_trajectory(model.trajectory_path, model.episode_index, model.name)
            n = min(len(att), len(traj))
            att = att[:n]
            traj = traj[:n]

            if obstacles_xy is not None:
                clearance = compute_clearance_profile(traj, obstacles_xy)
                stages = split_semantic_stages(clearance, enter_distance, leave_distance)
            else:
                print(f"[提示] {model.name}: 未提供 obstacles，使用比例切分阶段")
                stages = split_by_ratio(n, fallback_ratios)
        else:
            n = len(att)
            print(f"[提示] {model.name}: 未提供 trajectory_path，使用比例切分阶段")
            stages = split_by_ratio(n, fallback_ratios)

        stage_meta[model.name] = stages

        for stage_name, (start, end) in stages.items():
            seg = att[start:end]
            if len(seg) == 0:
                continue

            mean_w = seg.mean(axis=0)
            interp_profile = interpolate_to_common_axis(mean_w, bins)
            stage_profiles[stage_name].append((model.name, seq_len, interp_profile))

            m = stage_metrics(seg, recent_fraction)
            metrics_rows.append(
                {
                    "model": model.name,
                    "k": seq_len,
                    "stage": stage_name,
                    **m,
                }
            )

    if len(metrics_rows) == 0:
        raise RuntimeError("未生成任何指标，请检查输入文件")

    metrics_csv = os.path.join(output_dir, "stage_metrics.csv")
    save_metrics_csv(metrics_csv, metrics_rows, mode="stage")

    profile_png = os.path.join(output_dir, "stage_attention_profiles.png")
    plot_stage_profiles(profile_png, stage_profiles)

    metric_png = os.path.join(output_dir, "stage_metrics_heatmaps.png")
    plot_stage_metrics(metric_png, metrics_rows)

    meta_json = os.path.join(output_dir, "stage_boundaries.json")
    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(stage_meta, f, indent=2, ensure_ascii=False)

    print("\n=== 语义阶段对比分析完成 ===")
    print(f"指标表: {metrics_csv}")
    print(f"阶段注意力曲线图: {profile_png}")
    print(f"阶段指标热力图: {metric_png}")
    print(f"阶段边界记录: {meta_json}")


def run_observation_event_mode(config: Dict[str, object]) -> None:
    models = parse_models(config)
    output_dir = str(config.get("output_dir", "./attn_stage_compare_results"))
    os.makedirs(output_dir, exist_ok=True)

    raw_obstacles = config.get("obstacles", None)
    if raw_obstacles is None:
        raise ValueError("observation_event 模式必须提供 obstacles（固定障碍物坐标）")
    obstacles_xy = parse_obstacles(raw_obstacles)

    recent_fraction = float(config.get("recent_fraction", 0.3))
    bins = int(config.get("resample_bins", 50))

    detection_radius = float(config.get("detection_radius", 150.0))
    enter_distance = float(config.get("enter_distance", 120.0))
    leave_distance = float(config.get("leave_distance", 150.0))
    approach_delta = float(config.get("approach_delta", 2.0))
    leave_delta = float(config.get("leave_delta", 2.0))
    sustain_steps = int(config.get("sustain_steps", 3))
    switch_cooldown = int(config.get("switch_cooldown", 5))
    smoothing_alpha = float(config.get("smoothing_alpha", 0.3))

    window_left = int(config.get("event_window_left", 10))
    window_right = int(config.get("event_window_right", 0))
    min_window_len = int(config.get("event_min_window_len", 4))

    event_profiles: Dict[str, List[Tuple[str, int, np.ndarray]]] = {
        "switch": [],
        "approach": [],
        "leave": [],
    }
    metrics_rows: List[Dict[str, object]] = []
    event_meta: Dict[str, Dict[str, object]] = {}

    for model in models:
        if not model.trajectory_path:
            raise ValueError(f"[{model.name}] observation_event 模式必须提供 trajectory_path")

        att = load_attention(model.attention_path, model.name)
        traj = load_trajectory(model.trajectory_path, model.episode_index, model.name)

        n = min(len(att), len(traj))
        att = att[:n]
        traj = traj[:n]
        seq_len = att.shape[1]

        pair_ids, risk = compute_observation_set_signals(traj, obstacles_xy, detection_radius)
        events = detect_observation_events(
            pair_ids=pair_ids,
            risk_raw=risk,
            enter_distance=enter_distance,
            leave_distance=leave_distance,
            approach_delta=approach_delta,
            leave_delta=leave_delta,
            sustain_steps=sustain_steps,
            switch_cooldown=switch_cooldown,
            smoothing_alpha=smoothing_alpha,
        )
        windows = extract_event_windows(events, n, window_left, window_right, min_window_len)

        event_meta[model.name] = {
            "num_steps": int(n),
            "num_events_total": int(len(events)),
            "num_windows_total": int(len(windows)),
            "events": events,
        }

        for event_type in ["switch", "approach", "leave"]:
            w_type = [w for w in windows if w["type"] == event_type]
            if len(w_type) == 0:
                continue

            segs = [att[int(w["start"]) : int(w["end"])] for w in w_type]
            cat = np.concatenate(segs, axis=0)

            mean_w = cat.mean(axis=0)
            interp_profile = interpolate_to_common_axis(mean_w, bins)
            event_profiles[event_type].append((model.name, seq_len, interp_profile))

            m = stage_metrics(cat, recent_fraction)
            metrics_rows.append(
                {
                    "model": model.name,
                    "k": seq_len,
                    "event_type": event_type,
                    "num_windows": int(len(w_type)),
                    **m,
                }
            )

    if len(metrics_rows) == 0:
        raise RuntimeError("未生成任何事件窗口指标，请检查阈值、窗口和轨迹数据")

    metrics_csv = os.path.join(output_dir, "event_window_metrics.csv")
    save_metrics_csv(metrics_csv, metrics_rows, mode="event")

    profile_paths: Dict[str, str] = {}
    for event_type in ["switch", "approach", "leave"]:
        profile_path = os.path.join(output_dir, f"event_profile_{event_type}.png")
        plot_single_event_profile(profile_path, event_type, event_profiles[event_type])
        profile_paths[event_type] = profile_path

    metric_heatmap_specs = [
        ("mean_entropy_norm", "归一化熵", "event_metric_heatmap_entropy.png"),
        ("mean_recency_center", "近期中心", "event_metric_heatmap_recency_center.png"),
        ("mean_recent_ratio", "近期占比", "event_metric_heatmap_recent_ratio.png"),
    ]
    metric_paths: Dict[str, str] = {}
    for metric_key, metric_label_cn, filename in metric_heatmap_specs:
        metric_path = os.path.join(output_dir, filename)
        plot_metric_event_model_heatmap(metric_path, metrics_rows, metric_key, metric_label_cn)
        metric_paths[metric_key] = metric_path

    meta_json = os.path.join(output_dir, "event_boundaries.json")
    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(event_meta, f, indent=2, ensure_ascii=False)

    print("\n=== 观测集合事件对比分析完成 ===")
    print(f"指标表: {metrics_csv}")
    print(f"事件曲线图(switch): {profile_paths['switch']}")
    print(f"事件曲线图(approach): {profile_paths['approach']}")
    print(f"事件曲线图(leave): {profile_paths['leave']}")
    print(f"事件热力图(归一化熵): {metric_paths['mean_entropy_norm']}")
    print(f"事件热力图(近期中心): {metric_paths['mean_recency_center']}")
    print(f"事件热力图(近期占比): {metric_paths['mean_recent_ratio']}")
    print(f"事件记录: {meta_json}")


def run(config: Dict[str, object]) -> None:
    mode = str(config.get("analysis_mode", "observation_event")).strip().lower()
    if mode in {"observation_event", "event", "obs_event"}:
        run_observation_event_mode(config)
    else:
        run_stage_mode(config)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="语义阶段对齐 + 观测集合事件对齐 的多K注意力对比工具"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="attn_compare_config.json",
        help="JSON配置文件路径",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="在 --config 路径写出模板配置后退出",
    )
    args = parser.parse_args()

    if args.init_config:
        template = default_config_template()
        with open(args.config, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        print(f"已生成配置模板: {args.config}")
        return

    if not os.path.exists(args.config):
        raise FileNotFoundError(
            f"未找到配置文件: {args.config}。请先运行: python attention_analy.py --init-config"
        )

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    run(config)


if __name__ == "__main__":
    main()
