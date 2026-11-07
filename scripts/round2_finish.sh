#!/usr/bin/env bash
set -euo pipefail
cd /home/ot/Students/hs/sailboat-dynamic-routing-v0
test "$(realpath .)" = /home/ot/Students/hs/sailboat-dynamic-routing-v0
run=runs/round2_20261011
python_bin=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
trap 'echo failed > "$run/phase.txt"' ERR
echo waiting_for_training > "$run/phase.txt"
while test ! -f "$run/train_20261011/complete.json" || test ! -f "$run/train_20261012/complete.json"; do
  for train_seed in 20261011 20261012; do
    if test ! -f "$run/train_${train_seed}/complete.json"; then
      kill -0 "$(cat "$run/train_${train_seed}.pid")"
    fi
  done
  sleep 10
done
echo freeze_and_verify > "$run/phase.txt"
"$python_bin" scripts/round2_select.py
"$python_bin" scripts/verify_checkpoint.py checkpoints/round2/20261011/resume.pt
"$python_bin" scripts/verify_checkpoint.py checkpoints/round2/20261012/resume.pt
tar -czf "$run/selected_checkpoints.tar.gz" checkpoints/round2
echo old_key_cases > "$run/phase.txt"
"$python_bin" scripts/round2_confirm.py --key-cases
echo confirmation50 > "$run/phase.txt"
"$python_bin" scripts/round2_confirm.py
echo trajectory_checks > "$run/phase.txt"
"$python_bin" scripts/check_trajectories.py "$run/confirmation50/seed_20261011"
"$python_bin" scripts/check_trajectories.py "$run/confirmation50/seed_20261012"
"$python_bin" scripts/round2_events.py
echo ready_for_report > "$run/phase.txt"
