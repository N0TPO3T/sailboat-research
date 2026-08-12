"""
MPC 测试结果分析脚本

从保存好的 txt 文件中计算：
1) 航行距离
2) 消耗时间
3) 帆角/舵角变化总量
4) 帆角/舵角变化率

默认扫描当前目录下形如 MPC-* 的子目录。
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class EpisodeMetrics:
	case_name: str
	steps: int
	sail_distance_m: float
	elapsed_time_s: float
	sail_change_rad: float
	rudder_change_rad: float
	sail_change_rate_rad_s: float
	rudder_change_rate_rad_s: float


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Analyze MPC txt logs")
	parser.add_argument(
		"--root",
		type=str,
		default=None,
		help="根目录（默认脚本所在目录）",
	)
	parser.add_argument(
		"--pattern",
		type=str,
		default="MPC-*",
		help="测试目录匹配模式（默认 MPC-*）",
	)
	parser.add_argument(
		"--obs_file",
		type=str,
		default="observations.txt",
		help="观测文件名",
	)
	parser.add_argument(
		"--actions_file",
		type=str,
		default="actions.txt",
		help="动作文件名（用于步数兜底）",
	)
	parser.add_argument(
		"--config_file",
		type=str,
		default="config.txt",
		help="配置文件名（用于步数兜底）",
	)
	return parser.parse_args()


def _ensure_2d_array(arr: np.ndarray) -> np.ndarray:
	if arr.ndim == 1:
		return arr.reshape(1, -1)
	return arr


def _load_csv_txt(path: Path) -> np.ndarray:
	data = np.loadtxt(path, delimiter=",")
	return _ensure_2d_array(data)


def _parse_steps_from_config(config_path: Path) -> int | None:
	if not config_path.exists():
		return None

	text = config_path.read_text(encoding="utf-8", errors="ignore")
	match = re.search(r"总步数\s*[:：]\s*(\d+)", text)
	if match:
		return int(match.group(1))
	return None


def _compute_elapsed_time_from_obs(obs: np.ndarray) -> float:
	if obs.shape[1] <= 11:
		return float(max(obs.shape[0] - 1, 0))

	t = obs[:, 11]
	dt = np.diff(t)
	dt_pos = dt[dt > 0]
	if dt_pos.size == 0:
		return float(max(obs.shape[0] - 1, 0))
	return float(np.sum(dt_pos))


def _compute_steps(obs: np.ndarray, actions_path: Path, config_path: Path) -> int:
	if obs.shape[0] >= 2:
		return int(obs.shape[0] - 1)

	if actions_path.exists():
		actions = _load_csv_txt(actions_path)
		return int(actions.shape[0])

	cfg_steps = _parse_steps_from_config(config_path)
	if cfg_steps is not None:
		return cfg_steps

	return 0


def analyze_case(case_dir: Path, obs_file: str, actions_file: str, config_file: str) -> EpisodeMetrics:
	obs_path = case_dir / obs_file
	actions_path = case_dir / actions_file
	config_path = case_dir / config_file

	if not obs_path.exists():
		raise FileNotFoundError(f"Missing file: {obs_path}")

	obs = _load_csv_txt(obs_path)
	if obs.shape[1] <= 9:
		raise ValueError(f"Observation columns < 10, cannot parse sail/rudder from {obs_path}")

	steps = _compute_steps(obs, actions_path, config_path)

	dx = np.diff(obs[:, 0])
	dy = np.diff(obs[:, 1])
	sail_distance_m = float(np.sum(np.sqrt(dx * dx + dy * dy)))

	sail_change_rad = float(np.sum(np.abs(np.diff(obs[:, 8]))))
	rudder_change_rad = float(np.sum(np.abs(np.diff(obs[:, 9]))))

	elapsed_time_s = _compute_elapsed_time_from_obs(obs)
	if elapsed_time_s <= 0:
		sail_change_rate = 0.0
		rudder_change_rate = 0.0
	else:
		sail_change_rate = sail_change_rad / elapsed_time_s
		rudder_change_rate = rudder_change_rad / elapsed_time_s

	return EpisodeMetrics(
		case_name=case_dir.name,
		steps=steps,
		sail_distance_m=sail_distance_m,
		elapsed_time_s=elapsed_time_s,
		sail_change_rad=sail_change_rad,
		rudder_change_rad=rudder_change_rad,
		sail_change_rate_rad_s=sail_change_rate,
		rudder_change_rate_rad_s=rudder_change_rate,
	)


def print_case_table(results: list[EpisodeMetrics]) -> None:
	print("\n" + "=" * 108)
	print(
		f"{'Case':<12s} {'Steps':>7s} {'Distance(m)':>14s} {'Time(s)':>12s} "
		f"{'SailChange(deg)':>16s} {'RudderChange(deg)':>18s} {'SailRate(deg/s)':>17s} {'RudderRate(deg/s)':>19s}"
	)
	print("-" * 108)

	for item in results:
		print(
			f"{item.case_name:<12s} {item.steps:>7d} {item.sail_distance_m:>14.2f} {item.elapsed_time_s:>12.3f} "
			f"{np.rad2deg(item.sail_change_rad):>13.2f} {np.rad2deg(item.rudder_change_rad):>15.2f} "
			f"{np.rad2deg(item.sail_change_rate_rad_s):>17.2f} {np.rad2deg(item.rudder_change_rate_rad_s):>19.2f}"
		)

	print("=" * 108)


def print_summary(results: list[EpisodeMetrics]) -> None:
	dist = np.array([x.sail_distance_m for x in results], dtype=float)
	time_s = np.array([x.elapsed_time_s for x in results], dtype=float)
	sail_change_deg = np.rad2deg(np.array([x.sail_change_rad for x in results], dtype=float))
	rudder_change_deg = np.rad2deg(np.array([x.rudder_change_rad for x in results], dtype=float))
	sail_rate_deg_s = np.rad2deg(np.array([x.sail_change_rate_rad_s for x in results], dtype=float))
	rudder_rate_deg_s = np.rad2deg(np.array([x.rudder_change_rate_rad_s for x in results], dtype=float))

	print("\nSummary (Mean +- Std)")
	print("-" * 56)
	print(f"Distance (m):          {dist.mean():.2f} +- {dist.std():.2f}")
	print(f"Elapsed Time (s):      {time_s.mean():.3f} +- {time_s.std():.3f}")
	print(f"Sail Change (deg):     {sail_change_deg.mean():.2f} +- {sail_change_deg.std():.2f}")
	print(f"Rudder Change (deg):   {rudder_change_deg.mean():.2f} +- {rudder_change_deg.std():.2f}")
	print(f"Sail Rate (deg/s):     {sail_rate_deg_s.mean():.2f} +- {sail_rate_deg_s.std():.2f}")
	print(f"Rudder Rate (deg/s):   {rudder_rate_deg_s.mean():.2f} +- {rudder_rate_deg_s.std():.2f}")


def main() -> None:
	opt = parse_args()
	script_dir = Path(__file__).resolve().parent
	root = Path(opt.root).resolve() if opt.root else script_dir

	case_dirs = sorted([p for p in root.glob(opt.pattern) if p.is_dir()])
	if not case_dirs:
		fallback = root / "part4" / "MPC"
		if fallback.exists() and fallback.is_dir():
			case_dirs = sorted([p for p in fallback.glob(opt.pattern) if p.is_dir()])
			if case_dirs:
				root = fallback

	if not case_dirs:
		raise FileNotFoundError(f"No matched directories under {root}: pattern={opt.pattern}")

	results: list[EpisodeMetrics] = []
	failed: list[tuple[str, str]] = []

	for case_dir in case_dirs:
		try:
			metrics = analyze_case(case_dir, opt.obs_file, opt.actions_file, opt.config_file)
			results.append(metrics)
		except Exception as exc:
			failed.append((case_dir.name, str(exc)))

	if not results:
		raise RuntimeError("No valid MPC case analyzed.")

	print_case_table(results)
	print_summary(results)

	if failed:
		print("\nSkipped cases:")
		for name, err in failed:
			print(f"- {name}: {err}")


if __name__ == "__main__":
	main()
