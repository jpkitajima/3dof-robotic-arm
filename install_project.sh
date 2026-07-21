#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install_scripts_dir="${script_dir}/scripts/install"
ros_setup_script="/opt/ros/jazzy/setup.bash"
device_path="${1:-}"

source_setup_script() {
	local setup_script="$1"

	set +u
	source "$setup_script"
	set -u
}

echo "Installing ROS 2 Jazzy..."
bash "${install_scripts_dir}/install_ros_jazzy.sh"

echo "Installing udev rule for the robot arm serial device..."
bash "${install_scripts_dir}/install_udev_rule.sh" "${device_path}"

echo "Installing Python dependencies..."
bash "${install_scripts_dir}/install_python_deps.sh"

if [[ ! -f "$ros_setup_script" ]]; then
	echo "ROS Jazzy does not appear to be installed at $ros_setup_script." >&2
	exit 1
fi

echo "Building the workspace with colcon..."
source_setup_script "$ros_setup_script"
cd "$script_dir"
colcon build

echo "Setup complete. Replug the robot arm if device access does not update immediately."
echo "You can now run ./run.sh"