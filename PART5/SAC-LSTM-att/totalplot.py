from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch


FONT_SCALE = 1.75


def setup_chinese_font() -> None:
    plt.rcParams["font.family"] = "SimSun"
    plt.rcParams["font.sans-serif"] = [
        "SimSun",
        "NSimSun",
        "Songti SC",
        "STSong",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.labelweight"] = "bold"


def draw_wind_indicator(ax: plt.Axes, wind_dir_rad: float, hint_fs: float) -> None:
    inset = ax.inset_axes([0.03, 0.77, 0.18, 0.18])
    inset.set_aspect("equal")
    inset.set_xlim(-1.5, 1.5)
    inset.set_ylim(-1.5, 1.5)
    inset.axis("off")

    circle_r = 0.78
    circle = plt.Circle((0, 0), circle_r, fill=False, linewidth=1.2, color="#7f8c8d")
    inset.add_patch(circle)

    dir_x = np.cos(wind_dir_rad)
    dir_y = np.sin(wind_dir_rad)
    arrow = FancyArrowPatch(
        (0, 0),
        (0.66 * dir_x, 0.66 * dir_y),
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=3.2,
        color="black",
    )
    inset.add_patch(arrow)

    inset.text(
        0,
        -1.42,
        "风向",
        ha="center",
        va="top",
        fontsize=hint_fs,
        fontweight="bold",
        color="black",
        bbox=dict(boxstyle="round,pad=0.10", facecolor="white", edgecolor="none", alpha=0.90),
        clip_on=False,
    )


def plot_single_result(folder: Path) -> Path:
    obs_path = folder / "observations_raw.txt"
    wind_path = folder / "wind_info.txt"
    if not obs_path.exists() or not wind_path.exists():
        raise FileNotFoundError(f"缺少必要文件: {folder}")

    obs = pd.read_csv(obs_path)
    wind = pd.read_csv(wind_path)

    x = obs["obs_0"].to_numpy(dtype=float)
    y = obs["obs_1"].to_numpy(dtype=float)
    sail_angle_deg = np.rad2deg(obs["obs_8"].to_numpy(dtype=float))
    rudder_angle_deg = np.rad2deg(obs["obs_9"].to_numpy(dtype=float))

    target_x = float(obs["obs_12"].iloc[0])
    target_y = float(obs["obs_13"].iloc[0])

    wind_dir_series = wind["wind_direction"].to_numpy(dtype=float)
    wind_direction_rad = float(
        np.arctan2(np.mean(np.sin(wind_dir_series)), np.mean(np.cos(wind_dir_series)))
    )

    steps = np.arange(len(obs), dtype=int)

    fig = plt.figure(figsize=(18, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.55, 1.0], height_ratios=[1, 1])

    ax_path = fig.add_subplot(gs[:, 0])
    ax_sail = fig.add_subplot(gs[0, 1])
    ax_rudder = fig.add_subplot(gs[1, 1])

    legend_font_size = 12 * FONT_SCALE
    legend_prop = {"family": "SimSun", "size": legend_font_size, "weight": "bold"}

    ax_path.plot(x, y, color="#1f77b4", linewidth=2.4, label="航行轨迹")
    ax_path.scatter(x[0], y[0], s=150, color="#2ca02c", marker="o", zorder=4, label="起点")
    ax_path.scatter(x[-1], y[-1], s=150, color="#d62728", marker="X", zorder=4, label="终点")
    ax_path.scatter(target_x, target_y, s=150, color="#ff7f0e", marker="*", zorder=4, label="目标点")
    ax_path.set_title("路径图", fontsize=15 * FONT_SCALE, pad=10, fontweight="bold")
    ax_path.set_xlabel("X 位置 / 米", fontsize=12 * FONT_SCALE, fontweight="bold")
    ax_path.set_ylabel("Y 位置 / 米", fontsize=12 * FONT_SCALE, fontweight="bold")
    ax_path.set_xlim(-100, 600)
    ax_path.set_ylim(-300, 300)
    ax_path.grid(True, linestyle="--", alpha=0.35)
    ax_path.set_aspect("equal", adjustable="datalim")
    ax_path.legend(loc="best", prop=legend_prop, frameon=True)
    draw_wind_indicator(ax_path, wind_direction_rad, hint_fs=legend_font_size)

    ax_sail.plot(steps, sail_angle_deg, color="#9467bd", linewidth=2.0, label="帆角（实际）")
    ax_sail.set_title("帆角变化", fontsize=14 * FONT_SCALE, pad=8, fontweight="bold")
    ax_sail.set_xlabel("时间步", fontsize=12 * FONT_SCALE, fontweight="bold")
    ax_sail.set_ylabel("角度 / 度", fontsize=12 * FONT_SCALE, fontweight="bold")
    ax_sail.set_ylim(-95, 95)
    ax_sail.grid(True, linestyle="--", alpha=0.35)
    ax_sail.legend(loc="best", prop=legend_prop, frameon=True)

    ax_rudder.plot(steps, rudder_angle_deg, color="#8c564b", linewidth=2.0, label="舵角（实际）")
    ax_rudder.set_title("舵角变化", fontsize=14 * FONT_SCALE, pad=8, fontweight="bold")
    ax_rudder.set_xlabel("时间步", fontsize=12 * FONT_SCALE, fontweight="bold")
    ax_rudder.set_ylabel("角度 / 度", fontsize=12 * FONT_SCALE, fontweight="bold")
    ax_rudder.set_ylim(-35, 35)
    ax_rudder.grid(True, linestyle="--", alpha=0.35)
    ax_rudder.legend(loc="best", prop=legend_prop, frameon=True)

    for ax in (ax_path, ax_sail, ax_rudder):
        ax.tick_params(axis="both", labelsize=11 * FONT_SCALE)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight("bold")
    
    output_path = folder / "总览图_路径与帆舵角.jpg"
    fig.savefig(
    output_path,
    format="jpg",
    dpi=600,  # 大于 400
    bbox_inches="tight",
    pil_kwargs={"quality": 95},
)

    # output_path = folder / "总览图_路径与帆舵角.svg"
    # fig.savefig(output_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return output_path


def collect_target_folders(base_dir: Path) -> list[Path]:
    required_suffix = {"0", "90", "150", "180"}
    selected = []
    for item in sorted(base_dir.iterdir()):
        if not item.is_dir():
            continue
        suffix = item.name.rsplit("_", 1)[-1]
        if suffix in required_suffix:
            selected.append(item)
    return selected


def main() -> None:
    setup_chinese_font()
    base_dir = Path(__file__).resolve().parent
    folders = collect_target_folders(base_dir)
    if not folders:
        raise RuntimeError("当前目录下未找到后缀为 0/90/150/180 的结果文件夹。")

    print("开始绘图，共", len(folders), "个文件夹")
    for folder in folders:
        try:
            output = plot_single_result(folder)
            print(f"已生成: {output}")
        except Exception as exc:
            print(f"绘制失败: {folder} -> {exc}")


if __name__ == "__main__":
    main()
