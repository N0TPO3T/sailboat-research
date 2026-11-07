#!/usr/bin/env bash
set -euo pipefail
cd /home/ot/Students/hs/sailboat-dynamic-routing-v0
test "$(realpath .)" = /home/ot/Students/hs/sailboat-dynamic-routing-v0
run=runs/round3_20261011_2308
test ! -e "$run/pipeline.pid"
test -f "$run/implementation_check.json"
nohup bash scripts/round3_finish.sh > "$run/pipeline.log" 2>&1 &
echo $! > "$run/pipeline.pid"
cat "$run/pipeline.pid"
