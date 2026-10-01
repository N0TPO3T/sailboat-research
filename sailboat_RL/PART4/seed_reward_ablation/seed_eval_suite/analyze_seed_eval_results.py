#!/usr/bin/env python
"""Create figures and a Markdown analysis report for seed ablation results."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RESULT_DIR = SCRIPT_DIR / "seed_eval_results" / "seed_eval_20260518_002624"

MODEL_ORDER = ["SAC-LSTM", "SAC-nowind", "SAC-wind"]
SCENARIO_ORDER = [
    "random_wind",
    "fixed_wind_0",
    "fixed_wind_90",
    "fixed_wind_150",
    "fixed_wind_180",
]
SCENARIO_LABELS = {
    "random_wind": "Random",
    "fixed_wind_0": "0 deg",
    "fixed_wind_90": "90 deg",
    "fixed_wind_150": "150 deg",
    "fixed_wind_180": "180 deg",
}
MODEL_COLORS = {
    "SAC-LSTM": "#2F5597",
    "SAC-nowind": "#A23E48",
    "SAC-wind": "#2E7D32",
}
METRIC_LABELS = {
    "time_s": "Time (s)",
    "path_distance_m": "Path distance (m)",
    "sail_change_rate_deg_s": "Sail angle change rate (deg/s)",
    "rudder_change_rate_deg_s": "Rudder angle change rate (deg/s)",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize and analyze seed ablation evaluation results."
    )
    parser.add_argument(
        "--result_dir",
        type=Path,
        default=DEFAULT_RESULT_DIR,
        help="Directory containing seed evaluation CSV outputs.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help="Analysis output directory. Defaults to <result_dir>/analysis_report.",
    )
    return parser.parse_args()


def require_files(result_dir: Path) -> dict[str, Path]:
    files = {
        "episodes": result_dir / "episodes.csv",
        "boxplot": result_dir / "boxplot_values.csv",
        "checkpoint_summary": result_dir / "summary_by_checkpoint_scenario.csv",
        "family_summary": result_dir / "summary_by_model_family_scenario.csv",
        "manifest": result_dir / "run_manifest.json",
    }
    missing = [str(path) for path in files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required result files:\n" + "\n".join(missing))
    return files


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def ordered_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["model_family"] = pd.Categorical(
        out["model_family"], categories=MODEL_ORDER, ordered=True
    )
    out["scenario"] = pd.Categorical(
        out["scenario"], categories=SCENARIO_ORDER, ordered=True
    )
    return out.sort_values(["scenario", "model_family"])


def with_model_family(df: pd.DataFrame) -> pd.DataFrame:
    """Add model_family when checkpoint summaries only contain model_id."""
    if "model_family" in df.columns:
        return df
    out = df.copy()

    def infer(model_id: str) -> str:
        if model_id.startswith("saclstm_"):
            return "SAC-LSTM"
        if model_id.startswith("sac_nowind_"):
            return "SAC-nowind"
        if model_id.startswith("sac_wind_"):
            return "SAC-wind"
        raise ValueError(f"Cannot infer model_family from model_id={model_id!r}")

    out["model_family"] = out["model_id"].map(infer)
    return out


def save_figure(fig: plt.Figure, figures_dir: Path, name: str) -> None:
    fig.savefig(figures_dir / f"{name}.png")
    fig.savefig(figures_dir / f"{name}.svg")
    plt.close(fig)


def plot_success_rate(summary: pd.DataFrame, figures_dir: Path) -> None:
    df = ordered_frame(summary)
    x = np.arange(len(SCENARIO_ORDER), dtype=float)
    width = 0.24
    fig, ax = plt.subplots(figsize=(7.2, 3.4))

    for i, model in enumerate(MODEL_ORDER):
        sub = df[df["model_family"] == model].set_index("scenario")
        y = sub.reindex(SCENARIO_ORDER)["success_rate"].to_numpy(dtype=float) * 100.0
        low = sub.reindex(SCENARIO_ORDER)["success_rate_ci95_low"].to_numpy(dtype=float) * 100.0
        high = sub.reindex(SCENARIO_ORDER)["success_rate_ci95_high"].to_numpy(dtype=float) * 100.0
        yerr = np.vstack([np.maximum(y - low, 0.0), np.maximum(high - y, 0.0)])
        ax.bar(
            x + (i - 1) * width,
            y,
            width=width,
            color=MODEL_COLORS[model],
            label=model,
            edgecolor="black",
            linewidth=0.4,
            yerr=yerr,
            capsize=2,
            error_kw={"elinewidth": 0.8, "capthick": 0.8},
        )

    ax.set_ylabel("Success rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIO_ORDER])
    ax.set_ylim(0, 108)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    save_figure(fig, figures_dir, "success_rate_by_scenario")


def plot_success_heatmap(summary: pd.DataFrame, figures_dir: Path) -> None:
    pivot = (
        summary.pivot(index="model_family", columns="scenario", values="success_rate")
        .reindex(index=MODEL_ORDER, columns=SCENARIO_ORDER)
        * 100.0
    )
    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    image = ax.imshow(pivot.to_numpy(dtype=float), cmap="YlGnBu", vmin=0, vmax=100)
    ax.set_xticks(np.arange(len(SCENARIO_ORDER)))
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIO_ORDER])
    ax.set_yticks(np.arange(len(MODEL_ORDER)))
    ax.set_yticklabels(MODEL_ORDER)
    for row in range(len(MODEL_ORDER)):
        for col in range(len(SCENARIO_ORDER)):
            value = pivot.iloc[row, col]
            color = "white" if value > 70 else "black"
            ax.text(col, row, f"{value:.1f}", ha="center", va="center", color=color, fontsize=8)
    cbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Success rate (%)")
    for spine in ax.spines.values():
        spine.set_visible(False)
    save_figure(fig, figures_dir, "success_rate_heatmap")


def metric_values(
    boxplot: pd.DataFrame, metric: str, scenario: str, model: str
) -> np.ndarray:
    sub = boxplot[
        (boxplot["metric"] == metric)
        & (boxplot["scenario"] == scenario)
        & (boxplot["model_family"] == model)
        & (boxplot["success"] == 1)
    ]["value"]
    return sub.dropna().to_numpy(dtype=float)


def plot_metric_boxplot(
    boxplot: pd.DataFrame,
    figures_dir: Path,
    metric: str,
    output_name: str,
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 3.5))
    positions: list[float] = []
    data: list[np.ndarray] = []
    colors: list[str] = []
    centers = np.arange(len(SCENARIO_ORDER), dtype=float)
    offsets = [-0.26, 0.0, 0.26]

    for s_idx, scenario in enumerate(SCENARIO_ORDER):
        for m_idx, model in enumerate(MODEL_ORDER):
            values = metric_values(boxplot, metric, scenario, model)
            if values.size == 0:
                continue
            data.append(values)
            positions.append(centers[s_idx] + offsets[m_idx])
            colors.append(MODEL_COLORS[model])

    bp = ax.boxplot(
        data,
        positions=positions,
        widths=0.18,
        showfliers=False,
        patch_artist=True,
        medianprops={"color": "black", "linewidth": 1.0},
        whiskerprops={"linewidth": 0.8},
        capprops={"linewidth": 0.8},
        boxprops={"linewidth": 0.8},
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.72)

    ax.set_ylabel(ylabel)
    ax.set_xticks(centers)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIO_ORDER])
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    handles = [
        plt.Line2D(
            [0],
            [0],
            color=MODEL_COLORS[model],
            marker="s",
            linestyle="",
            markersize=7,
            label=model,
        )
        for model in MODEL_ORDER
    ]
    ax.legend(handles=handles, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    save_figure(fig, figures_dir, output_name)


def plot_sail_rudder_boxplots(boxplot: pd.DataFrame, figures_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.4), sharex=True)
    metrics = ["sail_change_rate_deg_s", "rudder_change_rate_deg_s"]
    offsets = [-0.26, 0.0, 0.26]
    centers = np.arange(len(SCENARIO_ORDER), dtype=float)

    for ax, metric in zip(axes, metrics):
        data: list[np.ndarray] = []
        positions: list[float] = []
        colors: list[str] = []
        for s_idx, scenario in enumerate(SCENARIO_ORDER):
            for m_idx, model in enumerate(MODEL_ORDER):
                values = metric_values(boxplot, metric, scenario, model)
                if values.size == 0:
                    continue
                data.append(values)
                positions.append(centers[s_idx] + offsets[m_idx])
                colors.append(MODEL_COLORS[model])
        bp = ax.boxplot(
            data,
            positions=positions,
            widths=0.18,
            showfliers=False,
            patch_artist=True,
            medianprops={"color": "black", "linewidth": 1.0},
            whiskerprops={"linewidth": 0.8},
            capprops={"linewidth": 0.8},
            boxprops={"linewidth": 0.8},
        )
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.72)
        ax.set_title("Sail" if metric.startswith("sail") else "Rudder")
        ax.set_ylabel("Change rate (deg/s)")
        ax.set_xticks(centers)
        ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIO_ORDER], rotation=20)
        ax.grid(axis="y", alpha=0.25, linewidth=0.6)

    handles = [
        plt.Line2D(
            [0],
            [0],
            color=MODEL_COLORS[model],
            marker="s",
            linestyle="",
            markersize=7,
            label=model,
        )
        for model in MODEL_ORDER
    ]
    fig.legend(handles=handles, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.08))
    save_figure(fig, figures_dir, "sail_rudder_rate_success_boxplot")


def plot_seed_sensitivity(checkpoint: pd.DataFrame, figures_dir: Path) -> None:
    df = ordered_frame(checkpoint)
    x = np.arange(len(SCENARIO_ORDER), dtype=float)
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.1), sharey=True)

    for ax, model in zip(axes, MODEL_ORDER):
        sub = df[df["model_family"] == model].copy()
        model_ids = sorted(sub["model_id"].unique())
        offsets = np.linspace(-0.12, 0.12, max(len(model_ids), 1))
        for offset, model_id in zip(offsets, model_ids):
            line = sub[sub["model_id"] == model_id].set_index("scenario").reindex(SCENARIO_ORDER)
            label = model_id.replace("saclstm_nowind_", "").replace("sac_nowind_", "").replace("sac_wind_", "")
            ax.plot(
                x + offset,
                line["success_rate"].to_numpy(dtype=float) * 100.0,
                marker="o",
                markersize=3.5,
                linewidth=1.0,
                label=label,
            )
        ax.set_title(model)
        ax.set_xticks(x)
        ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIO_ORDER], rotation=30)
        ax.grid(axis="y", alpha=0.25, linewidth=0.6)
        ax.legend(frameon=False, loc="lower left")
    axes[0].set_ylabel("Success rate (%)")
    axes[0].set_ylim(0, 105)
    save_figure(fig, figures_dir, "seed_sensitivity_success_rate")


def format_pct(value: float) -> str:
    return f"{value * 100.0:.2f}%"


def format_float(value: float, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{value:.{digits}f}"


def scenario_row(summary: pd.DataFrame, model: str, scenario: str) -> pd.Series:
    row = summary[(summary["model_family"] == model) & (summary["scenario"] == scenario)]
    if row.empty:
        raise KeyError(f"Missing summary row for {model} / {scenario}")
    return row.iloc[0]


def write_tables(summary: pd.DataFrame, checkpoint: pd.DataFrame, tables_dir: Path) -> None:
    compact_cols = [
        "model_family",
        "scenario",
        "episodes",
        "successes",
        "success_rate",
        "success_rate_ci95_low",
        "success_rate_ci95_high",
        "success_time_s_mean",
        "success_path_distance_m_mean",
        "success_sail_change_rate_deg_s_mean",
        "success_rudder_change_rate_deg_s_mean",
    ]
    ordered_frame(summary)[compact_cols].to_csv(
        tables_dir / "model_family_compact_summary.csv", index=False
    )
    ordered_frame(checkpoint)[
        ["model_family", "model_id", "scenario", "episodes", "successes", "success_rate"]
    ].to_csv(tables_dir / "checkpoint_success_rate_summary.csv", index=False)


def build_markdown_report(
    result_dir: Path,
    output_dir: Path,
    summary: pd.DataFrame,
    checkpoint: pd.DataFrame,
    episodes: pd.DataFrame,
    manifest: dict,
) -> str:
    random_rows = {
        model: scenario_row(summary, model, "random_wind") for model in MODEL_ORDER
    }
    fixed_150 = {
        model: scenario_row(summary, model, "fixed_wind_150") for model in MODEL_ORDER
    }
    fixed_180 = {
        model: scenario_row(summary, model, "fixed_wind_180") for model in MODEL_ORDER
    }
    sac_wind_best = scenario_row(summary, "SAC-wind", "fixed_wind_150")
    sac_lstm_random = random_rows["SAC-LSTM"]
    sac_wind_random = random_rows["SAC-wind"]
    sac_nowind_random = random_rows["SAC-nowind"]

    total_episodes = len(episodes)
    started_at = (
        manifest.get("created_at")
        or manifest.get("started_at")
        or manifest.get("timestamp")
        or "NA"
    )
    args = manifest.get("args", {})
    script = manifest.get("script", "NA")
    command = (
        f"{script} --num_workers {args.get('num_workers', 'NA')} --dvc {args.get('dvc', 'NA')}"
    )
    noise = {
        "enable_sensor_noise": args.get("enable_sensor_noise"),
        "sensor_noise_ratio": args.get("sensor_noise_ratio"),
        "enable_actuator_noise": args.get("enable_actuator_noise"),
        "actuator_noise_ratio": args.get("actuator_noise_ratio"),
    }

    lines = [
        "# 种子消融结果可视化与分析",
        "",
        "## 数据来源",
        "",
        f"- 结果目录：`{result_dir}`",
        f"- 分析输出：`{output_dir}`",
        f"- Episode 总数：`{total_episodes}`",
        f"- 运行时间记录：`{started_at}`",
        f"- 运行命令：`{command}`",
        f"- 随机风向 episode：`{args.get('random_episodes', 'NA')}`；固定风向 episode：`{args.get('fixed_episodes', 'NA')}`；固定风向：`{args.get('fixed_wind_degs', 'NA')}`",
        f"- 噪声设置：`{json.dumps(noise, ensure_ascii=False)}`",
        "",
        "## 统计口径",
        "",
        "- 成功率按全部 episode 统计，并使用原始 summary 中的 95% CI。",
        "- 航行时间、航行距离、帆角变化率、舵角变化率只在成功 episode 子集上统计。",
        "- `SAC-nowind` 在 `fixed_wind_150` 和 `fixed_wind_180` 下成功数为 0，因此这些场景没有成功航行的时间、距离和角度变化率分布；图中不做 0 填补。",
        "- 主结论按 `SAC-LSTM / SAC-nowind / SAC-wind` 聚合，seed100/seed200 的差异仅作为补充稳定性分析。",
        "",
        "## 主要发现",
        "",
        f"- 随机风向场景下，`SAC-wind` 成功率为 {format_pct(sac_wind_random['success_rate'])}，`SAC-LSTM` 为 {format_pct(sac_lstm_random['success_rate'])}，两者接近；`SAC-nowind` 只有 {format_pct(sac_nowind_random['success_rate'])}。",
        f"- 固定不利风向下，`SAC-wind` 保持最强鲁棒性：150 度成功率 {format_pct(sac_wind_best['success_rate'])}，180 度成功率 {format_pct(fixed_180['SAC-wind']['success_rate'])}。",
        f"- `SAC-LSTM` 在 0/90 度表现较好，但 150/180 度降至 {format_pct(fixed_150['SAC-LSTM']['success_rate'])} 和 {format_pct(fixed_180['SAC-LSTM']['success_rate'])}，说明无风向观测时 LSTM 历史信息能缓解但不能完全替代风向信息。",
        f"- `SAC-nowind` 对风向变化最敏感：150/180 度成功率均为 {format_pct(fixed_150['SAC-nowind']['success_rate'])}，是最明确的失效场景。",
        f"- 成功样本中，随机风向下 `SAC-LSTM` 平均成功时间 {format_float(sac_lstm_random['success_time_s_mean'])} s，`SAC-wind` 为 {format_float(sac_wind_random['success_time_s_mean'])} s；`SAC-wind` 的随机风向平均航行距离 {format_float(sac_wind_random['success_path_distance_m_mean'])} m，低于 `SAC-LSTM` 的 {format_float(sac_lstm_random['success_path_distance_m_mean'])} m。",
        "",
        "## 图表说明",
        "",
        "### 成功率",
        "",
        "![Success rate by scenario](figures/success_rate_by_scenario.png)",
        "",
        "该图直接比较三类模型在随机风向和四个固定初始风向下的成功率。误差线为 95% CI。`SAC-wind` 在全部固定风向中保持高成功率，`SAC-nowind` 在 150/180 度完全失效。",
        "",
        "![Success rate heatmap](figures/success_rate_heatmap.png)",
        "",
        "热力图更突出风向敏感性：`SAC-nowind` 的性能随风向恶化出现断崖式下降，而 `SAC-wind` 的颜色分布最稳定。",
        "",
        "### 成功航行效率",
        "",
        "![Successful sailing time](figures/time_success_boxplot.png)",
        "",
        "该箱式图只包含成功 episode。`SAC-nowind` 在 150/180 度没有成功样本，因此不显示箱体。随机风向下，`SAC-LSTM` 和 `SAC-wind` 的时间分布接近，`SAC-nowind` 的可成功样本不代表整体鲁棒性，因为失败 episode 已经由成功率体现。",
        "",
        "![Successful path distance](figures/path_distance_success_boxplot.png)",
        "",
        "航行距离同样只在成功样本内比较。`SAC-wind` 在随机风向下路径均值较低，说明其在成功航行中通常更直接；固定 180 度下路径长度上升，符合逆风或不利风向下机动距离增加的预期。",
        "",
        "### 控制平滑性",
        "",
        "![Sail and rudder change rates](figures/sail_rudder_rate_success_boxplot.png)",
        "",
        "帆角和舵角变化率按总变化量除以成功航行时间计算。该图用于比较控制动作的平滑性和频繁调整程度，应结合成功率一起解释：高成功率模型即使变化率略高，也可能代表其能主动适应风向扰动。",
        "",
        "### Seed 稳定性",
        "",
        "![Seed sensitivity](figures/seed_sensitivity_success_rate.png)",
        "",
        "该补充图展示每个模型 family 内 seed100/seed200 checkpoint 的成功率差异。主结论仍以聚合结果为准；若某模型在两个 seed 间差异很大，需要后续补充 seed300/seed400 后再判断稳定性。",
        "",
        "## 结论",
        "",
        "`SAC-wind` 是当前三类模型中风向鲁棒性最好的方案；`SAC-LSTM` 在随机风向总体接近 `SAC-wind`，但在 150/180 度固定初始风向下退化明显；`SAC-nowind` 缺少风向观测后，在不利风向下出现系统性失败。论文或汇报中建议把成功率作为主指标，把成功样本的时间、距离和角度变化率作为效率与控制行为的补充指标。",
        "",
        "## 输出文件",
        "",
        "- `figures/*.png`：300 dpi 位图。",
        "- `figures/*.svg`：矢量图。",
        "- `tables/model_family_compact_summary.csv`：聚合结果简表。",
        "- `tables/checkpoint_success_rate_summary.csv`：seed/checkpoint 成功率简表。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    result_dir = args.result_dir.resolve()
    output_dir = (args.output_dir or (result_dir / "analysis_report")).resolve()
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    files = require_files(result_dir)
    setup_style()

    episodes = pd.read_csv(files["episodes"])
    boxplot = pd.read_csv(files["boxplot"])
    checkpoint = with_model_family(pd.read_csv(files["checkpoint_summary"]))
    summary = pd.read_csv(files["family_summary"])
    with files["manifest"].open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    if len(episodes) != 10800:
        raise ValueError(f"Expected 10800 episode rows, got {len(episodes)}")
    expected_models = set(MODEL_ORDER)
    expected_scenarios = set(SCENARIO_ORDER)
    if set(summary["model_family"]) != expected_models:
        raise ValueError(f"Unexpected model families: {sorted(summary['model_family'].unique())}")
    if set(summary["scenario"]) != expected_scenarios:
        raise ValueError(f"Unexpected scenarios: {sorted(summary['scenario'].unique())}")

    plot_success_rate(summary, figures_dir)
    plot_success_heatmap(summary, figures_dir)
    plot_metric_boxplot(
        boxplot,
        figures_dir,
        "time_s",
        "time_success_boxplot",
        METRIC_LABELS["time_s"],
    )
    plot_metric_boxplot(
        boxplot,
        figures_dir,
        "path_distance_m",
        "path_distance_success_boxplot",
        METRIC_LABELS["path_distance_m"],
    )
    plot_sail_rudder_boxplots(boxplot, figures_dir)
    plot_seed_sensitivity(checkpoint, figures_dir)

    write_tables(summary, checkpoint, tables_dir)
    report = build_markdown_report(result_dir, output_dir, summary, checkpoint, episodes, manifest)
    (output_dir / "seed_ablation_analysis.md").write_text(report, encoding="utf-8")

    generated = sorted([p.name for p in figures_dir.glob("*.png")])
    print(f"Analysis output: {output_dir}")
    print(f"Figures: {len(generated)} PNG + {len(list(figures_dir.glob('*.svg')))} SVG")
    for name in generated:
        print(f"  - {name}")
    print(f"Report: {output_dir / 'seed_ablation_analysis.md'}")


if __name__ == "__main__":
    main()
