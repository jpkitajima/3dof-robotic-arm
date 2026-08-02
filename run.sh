#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ros_setup_script="/opt/ros/jazzy/setup.bash"
workspace_setup_script="${script_dir}/install/setup.bash"
install_scripts_dir="${script_dir}/scripts/install"
servo_adapter_mode="${1:-}"
device_path="${2:-}"

source_setup_script() {
	local setup_script="$1"

	set +u
	source "$setup_script"
	set -u
}

install_udev_rule_if_needed() {
	case "$servo_adapter_mode" in
		real|both)
			echo "Installing udev rule for the robot arm serial device..."
			if [[ -n "$device_path" ]]; then
				bash "${install_scripts_dir}/install_udev_rule.sh" "$device_path"
			else
				bash "${install_scripts_dir}/install_udev_rule.sh"
			fi
			;;
	esac
}

prompt_servo_adapter_mode() {
	local selected_mode

	while true; do
		read -r -p "Choose servo adapter mode (dummy/real): " selected_mode

		case "$selected_mode" in
			dummy|real)
				servo_adapter_mode="$selected_mode"
				return 0
				;;
			*)
				echo "Invalid mode '$selected_mode'. Enter 'dummy' or 'real'." >&2
				;;
		esac
		done
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

if [[ -z "$servo_adapter_mode" ]]; then
	prompt_servo_adapter_mode
fi

case "$servo_adapter_mode" in
	dummy|real|both)
		;;
	*)
		echo "Invalid mode '$servo_adapter_mode'. Use 'dummy', 'real', or 'both'." >&2
		exit 1
		;;
esac

install_udev_rule_if_needed

ros2 launch launcher robot_arm.launch.py "servo_adapter_mode:=${servo_adapter_mode}"
