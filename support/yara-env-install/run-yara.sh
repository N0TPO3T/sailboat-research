#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
test "$ROOT" = /home/ot/Students/hs/yara-env
mkdir -p "$ROOT/runtime/ros" "$ROOT/runtime/gazebo" "$ROOT/runtime/mpl" "$ROOT/runtime/xdg"
chmod 700 "$ROOT/runtime/xdg"
exec docker run --rm --init --name "hs-yara-$$" --label owner=hs-yara \
  --cpus=4 --memory=12g --network=none --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$ROOT,dst=/work" --workdir /work/workspace \
  -e HOME=/work -e ROS_HOME=/work/runtime/ros -e ROS_LOG_DIR=/work/logs/ros \
  -e GAZEBO_LOG_PATH=/work/runtime/gazebo -e MPLCONFIGDIR=/work/runtime/mpl \
  -e XDG_RUNTIME_DIR=/work/runtime/xdg -e LIBGL_ALWAYS_SOFTWARE=1 \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 \
  --entrypoint /bin/bash hs-yara:noetic-base /work/docker/entry.sh "$@"
