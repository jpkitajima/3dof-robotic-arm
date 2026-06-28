#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target_user="${SUDO_USER:-${USER:-}}"

if [[ -z "${target_user}" ]]; then
    echo "Unable to determine the target user." >&2
    exit 1
fi

if id -nG "${target_user}" | grep -qw dialout; then
    echo "User '${target_user}' is already in the dialout group."
else
    echo "Adding user '${target_user}' to the dialout group..."
    sudo usermod -a -G dialout "${target_user}"
    echo "Added user '${target_user}' to the dialout group."
fi

echo "Installing Python dependencies for launcher..."
python3 -m pip install -e "${script_dir}/src/launcher"

echo "Installing Python dependencies for robot_arm..."
python3 -m pip install -e "${script_dir}/src/robot_arm"

echo "Setup complete. Log out and log back in for new group membership to take effect."