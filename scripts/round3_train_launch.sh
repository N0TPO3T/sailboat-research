#!/usr/bin/env bash
set -euo pipefail
cd /home/ot/Students/hs/sailboat-dynamic-routing-v0
test "$(realpath .)" = /home/ot/Students/hs/sailboat-dynamic-routing-v0
run=runs/round3_20261011_2308
py=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python
test ! -e "$run/train_20261011"
test ! -e "$run/train_20261012"
nohup env PYTHONDONTWRITEBYTECODE=1 "$py" -u scripts/train_round3.py --adaptation headon_guard --dynamic-columns-only --mask-expired-metadata --handover-distribution actual_routes --seed 20261011 --scene-base 720000 --steps 40000 --dev-every 5000 --hours 4 --out "$run/train_20261011" > "$run/train_20261011.log" 2>&1 &
echo $! > "$run/train_20261011.pid"
nohup env PYTHONDONTWRITEBYTECODE=1 "$py" -u scripts/train_round3.py --adaptation headon_guard --dynamic-columns-only --mask-expired-metadata --handover-distribution actual_routes --seed 20261012 --scene-base 730000 --steps 40000 --dev-every 5000 --hours 4 --out "$run/train_20261012" > "$run/train_20261012.log" 2>&1 &
echo $! > "$run/train_20261012.pid"
cat "$run/train_20261011.pid" "$run/train_20261012.pid"
