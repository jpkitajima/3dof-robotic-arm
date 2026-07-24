#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ros_setup_script="/opt/ros/jazzy/setup.bash"
workspace_setup_script="${script_dir}/install/setup.bash"

source_setup_script() {
	local setup_script="$1"

	set +u
	source "$setup_script"
	set -u
}

if [[ ! -f "$ros_setup_script" ]]; then
	echo "ROS Jazzy does not appear to be installed at $ros_setup_script." >&2
	echo "Run ./install_project.sh first." >&2
	exit 1
fi

if [[ ! -f "$workspace_setup_script" ]]; then
	echo "The workspace has not been built yet." >&2
	echo "Run ./install_project.sh first." >&2
	exit 1
fi

source_setup_script "$ros_setup_script"
source_setup_script "$workspace_setup_script"

ros2 launch launcher robot_arm.launch.py servo_adapter_mode:=dummy
