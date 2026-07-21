#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
sudo_cmd=()

require_command() {
	local command_name="$1"

	if ! command -v "$command_name" >/dev/null 2>&1; then
		echo "Required command '$command_name' was not found." >&2
		exit 1
	fi
}

init_privilege_command() {
	if [[ "${EUID}" -eq 0 ]]; then
		sudo_cmd=()
		return
	fi

	require_command sudo
	sudo_cmd=(sudo)
}

ensure_pip() {
	if python3 -m pip --version >/dev/null 2>&1; then
		return
	fi

	echo "python3-pip was not found. Installing it..."
	"${sudo_cmd[@]}" apt update
	"${sudo_cmd[@]}" apt install -y python3-pip
}

main() {
	require_command python3
	init_privilege_command
	ensure_pip

	echo "Installing Python dependencies for launcher..."
	python3 -m pip install --break-system-packages -e "${repo_root}/src/launcher"

	echo "Installing Python dependencies for robot_arm..."
	python3 -m pip install --break-system-packages -e "${repo_root}/src/robot_arm"
}

main "$@"