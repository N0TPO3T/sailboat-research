"""
Audit imported reward-ablation SAC-LSTM checkpoints.

This script is read-only. It reports the latest matching actor/q checkpoint,
the latest normalizer checkpoint, final stats availability, and total_steps
when torch can load the stats file.
"""

from __future__ import annotations

import os
import re
import sys
import argparse
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")


EXPERIMENTS = [
    ("01_no_dense_progress_speed", "saclstm_no_dense_progress_speed_s14nowind"),
    ("02_no_action_penalty", "saclstm_no_action_penalty_s14nowind"),
    ("03_no_checkpoint", "saclstm_no_checkpoint_s14nowind"),
    ("04_no_arrival", "saclstm_no_arrival_s14nowind"),
    ("05_no_penalty", "saclstm_no_penalty_s14nowind"),
]


def load_torch():
    try:
        import torch  # type: ignore

        return torch, None
    except Exception as exc:  # pragma: no cover - depends on local env
        return None, str(exc)


def find_steps(model_dir: Path, prefix: str, kind: str) -> set[int]:
    pattern = re.compile(rf"^{re.escape(prefix)}_{kind}(\d+)\.pth$")
    steps: set[int] = set()
    for path in model_dir.glob(f"{prefix}_{kind}*.pth"):
        match = pattern.match(path.name)
        if match:
            steps.add(int(match.group(1)))
    return steps


def read_total_steps(stats_path: Path, torch_module) -> tuple[str, str | None]:
    if not stats_path.exists():
        return "missing", "missing final stats"
    if torch_module is None:
        return "unread", None
    try:
        data = torch_module.load(stats_path, map_location="cpu")
    except Exception as exc:
        return "error", f"could not load final stats: {exc}"
    if not isinstance(data, dict):
        return "unknown", "final stats is not a dict"
    return str(data.get("total_steps", "unknown")), None


def fmt_step(step: int | None) -> str:
    return str(step) if step is not None else "-"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit reward-ablation SAC-LSTM checkpoints")
    parser.add_argument("--model_dir_name", type=str, default="model_buf1e6")
    opt = parser.parse_args()

    root = Path(__file__).resolve().parent
    torch_module, torch_error = load_torch()
    issues: list[str] = []

    if torch_error:
        print(f"torch unavailable for final stats loading: {torch_error}")

    header = (
        "experiment",
        "prefix",
        "latest_actor_q",
        "latest_normalizer",
        "final_stats",
        "total_steps",
        "notes",
    )
    print("\t".join(header))

    for folder, prefix in EXPERIMENTS:
        exp_dir = root / folder
        model_dir = exp_dir / opt.model_dir_name
        actor_steps = find_steps(model_dir, prefix, "actor")
        q_steps = find_steps(model_dir, prefix, "q_critic")
        normalizer_steps = find_steps(model_dir, prefix, "normalizer")

        common_actor_q = actor_steps & q_steps
        latest_actor_q = max(common_actor_q) if common_actor_q else None
        latest_normalizer = max(normalizer_steps) if normalizer_steps else None
        stats_path = model_dir / f"{prefix}_final_training_stats.pth"
        total_steps, stats_issue = read_total_steps(stats_path, torch_module)

        notes: list[str] = []
        if not exp_dir.exists():
            notes.append("missing experiment directory")
        if not model_dir.exists():
            notes.append("missing model directory")
        if not actor_steps:
            notes.append("missing actor checkpoints")
        if not q_steps:
            notes.append("missing q checkpoints")
        if actor_steps - q_steps:
            notes.append(f"actor_without_q={sorted(actor_steps - q_steps)}")
        if q_steps - actor_steps:
            notes.append(f"q_without_actor={sorted(q_steps - actor_steps)}")
        if latest_actor_q is not None and latest_normalizer != latest_actor_q:
            notes.append("latest normalizer does not match latest actor/q")
        if total_steps.isdigit() and latest_actor_q is not None:
            saved_step_as_steps = latest_actor_q * 1000
            if int(total_steps) > saved_step_as_steps:
                notes.append(f"stats exceed saved checkpoint ({total_steps}>{saved_step_as_steps})")
        if stats_issue:
            notes.append(stats_issue)

        if any(
            note.startswith("missing")
            or note.startswith("actor_without_q")
            or note.startswith("q_without_actor")
            or note.startswith("latest normalizer")
            for note in notes
        ):
            issues.append(folder)

        print(
            "\t".join(
                [
                    folder,
                    prefix,
                    fmt_step(latest_actor_q),
                    fmt_step(latest_normalizer),
                    "yes" if stats_path.exists() else "no",
                    total_steps,
                    "; ".join(notes) if notes else "ok",
                ]
            )
        )

    if issues:
        print(f"\nImport audit found blocking issues in: {', '.join(issues)}")
        return 1

    print("\nImport audit completed without blocking checkpoint issues.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
