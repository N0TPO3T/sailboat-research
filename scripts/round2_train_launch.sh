#!/usr/bin/env bash
set -eu
cd /home/ot/Students/hs/sailboat-dynamic-routing-v0
test "$(realpath .)" = /home/ot/Students/hs/sailboat-dynamic-routing-v0
for train_seed in 20261011 20261012; do
  test ! -e "runs/round2_20261011/train_${train_seed}"
  test ! -e "runs/round2_20261011/train_${train_seed}.pid"
done
for train_seed in 20261011 20261012; do
  scene_base=$((720000 + (train_seed - 20261011) * 10000))
  nohup env PYTHONDONTWRITEBYTECODE=1 /home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python -u scripts/train.py \
    --dynamic-columns-only --mask-expired-metadata --handover-distribution actual_routes \
    --seed "$train_seed" --scene-base "$scene_base" --steps 40000 --dev-every 5000 --hours 4 \
    --out "runs/round2_20261011/train_${train_seed}" \
    > "runs/round2_20261011/train_${train_seed}.log" 2>&1 < /dev/null &
  echo "$!" > "runs/round2_20261011/train_${train_seed}.pid"
done
