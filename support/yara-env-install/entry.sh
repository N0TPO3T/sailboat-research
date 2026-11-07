#!/usr/bin/env bash
set -e
source /opt/ros/noetic/setup.bash
if [ -f /work/workspace/devel/setup.bash ]; then source /work/workspace/devel/setup.bash; fi
export PYTHONPATH="/work/python:/work/workspace/src/Yara_OVE/esailor:${PYTHONPATH:-}"
export GAZEBO_MODEL_DATABASE_URI=""
export GAZEBO_MODEL_PATH="/work/workspace/src/Yara_OVE/yara_description/models:/work/workspace/src/Yara_OVE/yara_gazebo/models:${GAZEBO_MODEL_PATH:-}"
export ROS_HOSTNAME=127.0.0.1
export ROS_MASTER_URI=http://127.0.0.1:11311
exec "$@"
