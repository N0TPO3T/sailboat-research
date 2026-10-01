from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch


FONT_SCALE = 1.75


def setup_chinese_font() -> None:
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["font.sans-serif"] = ["Times New Roman"]
    plt.rcParams["font.serif"] = ["Times New Roman"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.labelweight"] = "bold"


def draw_wind_indicator(ax: plt.Axes, wind_dir_rad: float, hint_fs: float) -> None:
    inset = ax.inset_axes([0.04, 0.73, 0.17, 0.17])
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
        "Wind",
        ha="center",
        va="top",
        fontsize=hint_fs,
        fontweight="bold",
        color="black",
        bbox=dict(boxstyle="round,pad=0.10", facecolor="white", edgecolor="none", alpha=0.90),
        clip_on=False,
    )


def load_observations(folder: Path, is_mpc: bool) -> pd.DataFrame:
    if is_mpc:
        obs_path = folder / "observations.txt"
        if not obs_path.exists():
            raise FileNotFoundError(f"Missing file: {obs_path}")
        obs = pd.read_csv(obs_path, header=None)
        obs.columns = [f"obs_{i}" for i in range(obs.shape[1])]
        return obs

    obs_path = folder / "observations_raw.txt"
    if not obs_path.exists():
        raise FileNotFoundError(f"Missing file: {obs_path}")
    return pd.read_csv(obs_path)


def parse_wind_direction(folder: Path, fallback_deg: float) -> float:
    wind_info = folder / "wind_info.txt"
    if wind_info.exists():
        wind = pd.read_csv(wind_info)
        wind_dir_series = wind["wind_direction"].to_numpy(dtype=float)
        return float(
            np.arctan2(np.mean(np.sin(wind_dir_series)), np.mean(np.cos(wind_dir_series)))
        )

    config_path = folder / "config.txt"
    if config_path.exists():
        text = config_path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"风向角度\s*:\s*([\d.]+)", text)
        if match:
            return np.deg2rad(float(match.group(1)))

    return np.deg2rad(float(fallback_deg))


def extract_series(obs: pd.DataFrame) -> dict[str, np.ndarray | float]:
    return {
        "x": obs["obs_0"].to_numpy(dtype=float),
        "y": obs["obs_1"].to_numpy(dtype=float),
        "sail_deg": np.rad2deg(obs["obs_8"].to_numpy(dtype=float)),
        "rudder_deg": np.rad2deg(obs["obs_9"].to_numpy(dtype=float)),
        "target_x": float(obs["obs_12"].iloc[0]),
        "target_y": float(obs["obs_13"].iloc[0]),
    }


def find_folder(base_dir: Path, suffix: str, model: str) -> Path:
    if model == "MPC":
        folder = base_dir / f"MPC-{suffix}"
    else:
        folder = base_dir / f"saclstm_s14nowind_final_{suffix}"
    if not folder.exists():
        raise FileNotFoundError(f"Missing folder: {folder}")
    return folder


def plot_comparison_overview(base_dir: Path) -> Path:
    row_defs = [
        ("0", "Tailwind (0°)"),
        ("90", "Crosswind (90°)"),
        ("150", "Oblique Headwind (150°)"),
        ("180", "Headwind (180°)"),
    ]

    fig = plt.figure(figsize=(24, 26), constrained_layout=True)
    gs = fig.add_gridspec(4, 3, width_ratios=[1.08, 1.0, 1.0], hspace=0.08, wspace=0.04)

    legend_prop = {"size": 11 * FONT_SCALE, "weight": "bold"}
    line_styles = {
        "MPC": dict(color="#2F5597", linewidth=2.8, alpha=0.95),
        "SAC-LSTM": dict(color="#ED7D31", linewidth=2.8, alpha=0.95),
    }

    for row_idx, (suffix, wind_label) in enumerate(row_defs):
        mpc_folder = find_folder(base_dir, suffix, "MPC")
        sac_folder = find_folder(base_dir, suffix, "SAC-LSTM")

        mpc_data = extract_series(load_observations(mpc_folder, is_mpc=True))
        sac_data = extract_series(load_observations(sac_folder, is_mpc=False))
        wind_dir = parse_wind_direction(sac_folder, fallback_deg=float(suffix))

        ax_path = fig.add_subplot(gs[row_idx, 0])
        ax_sail = fig.add_subplot(gs[row_idx, 1])
        ax_rudder = fig.add_subplot(gs[row_idx, 2])

        ax_path.plot(mpc_data["x"], mpc_data["y"], label="MPC", **line_styles["MPC"])
        ax_path.plot(sac_data["x"], sac_data["y"], label="SAC-LSTM", **line_styles["SAC-LSTM"])
        ax_path.scatter(
            mpc_data["x"][0],
            mpc_data["y"][0],
            s=90,
            color="#1B5E20",
            marker="o",
            zorder=5,
            label="Start",
        )
        ax_path.scatter(
            sac_data["target_x"],
            sac_data["target_y"],
            s=100,
            color="#8B1E3F",
            marker="*",
            zorder=5,
            label="Target",
        )
        ax_path.set_xlabel("X Position (m)", fontsize=11 * FONT_SCALE, fontweight="bold")
        
        ax_path.set_ylabel("Y Position (m)", fontsize=11 * FONT_SCALE, fontweight="bold")
        ax_path.set_xlim(-50,550)
        ax_path.set_ylim(-300,300)

        ax_path.grid(True, linestyle="--", alpha=0.35, linewidth=0.9)
        ax_path.set_aspect("equal", adjustable="box")
        ax_path.legend(loc="best", prop=legend_prop, frameon=True)
        draw_wind_indicator(ax_path, wind_dir, hint_fs=9 * FONT_SCALE)
        ax_path.text(
            -0.30,
            1.03,
            wind_label,
            transform=ax_path.transAxes,
            ha="left",
            va="bottom",
            fontsize=13 * FONT_SCALE,
            fontweight="bold",
            clip_on=False,
        )

        mpc_steps = np.arange(len(mpc_data["sail_deg"]), dtype=int)
        sac_steps = np.arange(len(sac_data["sail_deg"]), dtype=int)

        ax_sail.plot(mpc_steps, mpc_data["sail_deg"], label="MPC", **line_styles["MPC"])
        ax_sail.plot(sac_steps, sac_data["sail_deg"], label="SAC-LSTM", **line_styles["SAC-LSTM"])
        ax_sail.set_xlabel("Step", fontsize=11 * FONT_SCALE, fontweight="bold")
        ax_sail.set_ylabel("Sail Angle (deg)", fontsize=11 * FONT_SCALE, fontweight="bold")
        ax_sail.set_ylim(-95,95)
        ax_sail.grid(True, linestyle="--", alpha=0.35, linewidth=0.9)
        ax_sail.legend(loc="best", prop=legend_prop, frameon=True)

        ax_rudder.plot(mpc_steps, mpc_data["rudder_deg"], label="MPC", **line_styles["MPC"])
        ax_rudder.plot(sac_steps, sac_data["rudder_deg"], label="SAC-LSTM", **line_styles["SAC-LSTM"])
        ax_rudder.set_xlabel("Step", fontsize=11 * FONT_SCALE, fontweight="bold")
        ax_rudder.set_ylabel("Rudder Angle (deg)", fontsize=11 * FONT_SCALE, fontweight="bold")
        ax_rudder.set_ylim(-35,35)
        ax_rudder.grid(True, linestyle="--", alpha=0.35, linewidth=0.9)
        ax_rudder.legend(loc="best", prop=legend_prop, frameon=True)

        for ax in (ax_path, ax_sail, ax_rudder):
            ax.tick_params(axis="both", labelsize=10 * FONT_SCALE)
            for tick in ax.get_xticklabels() + ax.get_yticklabels():
                tick.set_fontweight("bold")

    output_path = base_dir / "overview_4wind_mpc_saclstm.jpg"
    fig.savefig(
        output_path,
        format="jpg",
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"quality": 95},
    )
    plt.close(fig)
    return output_path


def main() -> None:
    setup_chinese_font()
    base_dir = Path(__file__).resolve().parent
    output = plot_comparison_overview(base_dir)
    print(f"Generated: {output}")


if __name__ == "__main__":
    main()
