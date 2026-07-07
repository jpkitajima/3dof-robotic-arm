#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
udev_rules_src="${script_dir}/udev/99-robot-arm.rules"
udev_rules_dst="/etc/udev/rules.d/99-robot-arm.rules"

if [[ ! -f "${udev_rules_src}" ]]; then
    echo "Missing udev rule file: ${udev_rules_src}" >&2
    exit 1
fi

echo "Installing udev rule for the supported USB serial adapter..."
sudo install -D -m 0644 "${udev_rules_src}" "${udev_rules_dst}"
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Installing Python dependencies for launcher..."
python3 -m pip install -e "${script_dir}/src/launcher"

echo "Installing Python dependencies for robot_arm..."
python3 -m pip install -e "${script_dir}/src/robot_arm"

cat <<'EOF'
Setup complete.

- If you are using the supported CH340/CH341-style USB serial adapter, unplug and replug it once so the new /dev/robot_arm_servo symlink appears.
- If you are using different USB hardware, set the real adapter path explicitly with:
    ros2 launch launcher robot_arm.launch.py servo_adapter_mode:=real servo_device_path:=/dev/serial/by-id/your-device
EOF