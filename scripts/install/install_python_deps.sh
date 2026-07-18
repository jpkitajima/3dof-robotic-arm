#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

echo "Installing Python dependencies for launcher..."
python3 -m pip install --break-system-packages -e "${repo_root}/src/launcher"

echo "Installing Python dependencies for robot_arm..."
python3 -m pip install --break-system-packages -e "${repo_root}/src/robot_arm"