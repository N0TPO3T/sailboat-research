#!/usr/bin/env bash
set -eo pipefail
export DISPLAY=:99
Xvfb :99 -screen 0 1600x900x24 -ac +extension GLX +render -noreset > /work/logs/xvfb.log 2>&1 &
XPID=$!
sleep 2
roslaunch yara_gazebo empty_ocean.launch gui:=false paused:=true verbose:=false > /work/logs/visual-gazebo.log 2>&1 &
RPID=$!
trap 'kill -INT "$RPID" 2>/dev/null || true; wait "$RPID" 2>/dev/null || true; kill "$XPID" 2>/dev/null || true' EXIT
timeout 200 python3 -u /work/transfer_audit/visual_demo.py
