#!/usr/bin/env bash
set -eo pipefail
roslaunch yara_gazebo empty_ocean.launch gui:=false paused:=true verbose:=true > /work/logs/gazebo-smoke.log 2>&1 &
LAUNCH_PID=$!
trap 'kill -INT "$LAUNCH_PID" 2>/dev/null || true; wait "$LAUNCH_PID" 2>/dev/null || true' EXIT
timeout 180 python3 /work/docker/smoke.py
