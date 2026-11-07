#!/usr/bin/env bash
set -eo pipefail
roslaunch yara_gazebo empty_ocean.launch gui:=false paused:=true verbose:=false > /work/logs/baseline-gazebo.log 2>&1 &
RPID=$!
trap 'kill -INT "$RPID" 2>/dev/null || true; wait "$RPID" 2>/dev/null || true' EXIT
python3 -u /work/transfer_audit/baseline_entry.py "$@"
