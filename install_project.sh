#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install_scripts_dir="${script_dir}/scripts/install"
device_path="${1:-}"

echo "Installing ROS 2 Jazzy..."
bash "${install_scripts_dir}/install_ros_jazzy.sh"

echo "Installing udev rule for the robot arm serial device..."
bash "${install_scripts_dir}/install_udev_rule.sh" "${device_path}"

echo "Installing Python dependencies..."
bash "${install_scripts_dir}/install_python_deps.sh"

echo "Setup complete. Replug the robot arm if device access does not update immediately."