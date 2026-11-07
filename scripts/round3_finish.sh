#!/usr/bin/env bash
set -euo pipefail
cd /home/ot/Students/hs/sailboat-dynamic-routing-v0
test "$(realpath .)" = /home/ot/Students/hs/sailboat-dynamic-routing-v0
run=runs/round3_20261011_2308
py=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
trap 'echo failed > "$run/phase.txt"' ERR
echo waiting_for_training > "$run/phase.txt"
while test ! -f "$run/train_20261011/complete.json" || test ! -f "$run/train_20261012/complete.json"; do
  for seed in 20261011 20261012; do
    if test ! -f "$run/train_${seed}/complete.json"; then kill -0 "$(cat "$run/train_${seed}.pid")"; fi
  done
  sleep 10
done
# The single implementation check is a prerequisite for confirmation, not a
# numerical performance gate. Do not generate new50 while it remains pending.
test -f "$run/implementation_check.json"
echo freeze_and_verify > "$run/phase.txt"
"$py" scripts/round3_select.py
"$py" scripts/verify_round3_checkpoint.py checkpoints/round3/20261011/resume.pt
"$py" scripts/verify_round3_checkpoint.py checkpoints/round3/20261012/resume.pt
tar -czf "$run/selected_checkpoints.tar.gz" checkpoints/round3
echo confirmation50 > "$run/phase.txt"
"$py" scripts/round3_confirm.py
echo trajectory_checks > "$run/phase.txt"
"$py" scripts/check_round3_trajectories.py "$run/confirmation50/seed_20261011"
"$py" scripts/check_round3_trajectories.py "$run/confirmation50/seed_20261012"
echo ready_for_report > "$run/phase.txt"
