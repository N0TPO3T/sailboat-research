#!/bin/bash
set -eo pipefail
export DISPLAY=:98
export GAZEBO_PLUGIN_PATH="/work/migration18/build:${GAZEBO_PLUGIN_PATH:-}"
Xvfb :98 -screen 0 1600x900x24 -ac +extension GLX +render -noreset > /work/migration18/logs/xvfb.log 2>&1 &
XPID=$!
# Wait for display readiness, unrelated to simulation stepping.
for i in $(seq 1 40); do [ -S /tmp/.X11-unix/X98 ] && break; sleep 0.1; done
sleep 1
roslaunch yara_gazebo empty_ocean.launch world:="${1:-/work/migration18/ocean.world}" "extra_gazebo_args:=${2:-}" gui:=false paused:=true verbose:=false > /work/migration18/logs/gazebo.log 2>&1 &
RPID=$!
trap 'kill -INT "$RPID" 2>/dev/null || true; kill "$XPID" 2>/dev/null || true' EXIT
python3 -u /work/migration18/bridge.py
