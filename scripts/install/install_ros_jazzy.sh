#!/usr/bin/env bash

set -euo pipefail

ros_package="${ROS_JAZZY_PACKAGE:-ros-jazzy-desktop}"
project_ros_packages=(
    ros-jazzy-urdf-launch
)
project_system_packages=(
    python3-aiohttp
    python3-serial
    python3-yaml
)
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

print_post_install_instructions() {
    local shell_name
    local setup_script
    local rc_file

    shell_name="$(basename "${SHELL:-bash}")"

    case "$shell_name" in
        zsh)
            setup_script="/opt/ros/jazzy/setup.zsh"
            rc_file="~/.zshrc"
            ;;
        *)
            setup_script="/opt/ros/jazzy/setup.bash"
            rc_file="~/.bashrc"
            ;;
    esac

    echo "ROS 2 Jazzy installation complete."
    echo "To use ROS in the current shell, run: source $setup_script"
    echo "To load ROS automatically in future shells, add this line to $rc_file:"
    echo "  source $setup_script"
}

ensure_supported_platform() {
    local ubuntu_codename

    . /etc/os-release
    ubuntu_codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"

    if [[ "$ubuntu_codename" != "noble" ]]; then
        echo "ROS 2 Jazzy Debian packages are only supported on Ubuntu Noble (24.04)." >&2
        echo "Detected Ubuntu codename: ${ubuntu_codename:-unknown}" >&2
        exit 1
    fi
}

install_locale() {
    echo "Configuring UTF-8 locale..."
    "${sudo_cmd[@]}" apt update
    "${sudo_cmd[@]}" apt install -y locales
    "${sudo_cmd[@]}" locale-gen en_US en_US.UTF-8
    "${sudo_cmd[@]}" update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
    export LANG=en_US.UTF-8
}

enable_ros_repositories() {
    local ros_apt_source_version
    local ubuntu_codename

    . /etc/os-release
    ubuntu_codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"

    echo "Enabling Ubuntu Universe and ROS 2 apt repositories..."
    "${sudo_cmd[@]}" apt install -y software-properties-common
    "${sudo_cmd[@]}" add-apt-repository -y universe

    "${sudo_cmd[@]}" apt update
    "${sudo_cmd[@]}" apt install -y curl

    ros_apt_source_version="$({
        curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest |
            grep -F 'tag_name' |
            awk -F '"' '{print $4}'
    })"

    if [[ -z "$ros_apt_source_version" ]]; then
        echo "Failed to determine the latest ros2-apt-source release." >&2
        exit 1
    fi

    curl -L -o /tmp/ros2-apt-source.deb \
        "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ros_apt_source_version}/ros2-apt-source_${ros_apt_source_version}.${ubuntu_codename}_all.deb"
    "${sudo_cmd[@]}" dpkg -i /tmp/ros2-apt-source.deb
}

install_ros_jazzy() {
    echo "Installing ROS 2 Jazzy package: $ros_package"
    "${sudo_cmd[@]}" apt update
    "${sudo_cmd[@]}" apt install -y "$ros_package"
}

install_ros_dev_tools() {
    echo "Installing ROS development tools..."
    "${sudo_cmd[@]}" apt update
    "${sudo_cmd[@]}" apt install -y ros-dev-tools
}

install_project_ros_packages() {
    echo "Installing project ROS packages: ${project_ros_packages[*]}"
    "${sudo_cmd[@]}" apt update
    "${sudo_cmd[@]}" apt install -y "${project_ros_packages[@]}"
}

install_project_system_packages() {
    echo "Installing project system packages: ${project_system_packages[*]}"
    "${sudo_cmd[@]}" apt update
    "${sudo_cmd[@]}" apt install -y "${project_system_packages[@]}"
}

main() {
    require_command grep
    require_command awk
    require_command dpkg

    init_privilege_command
    ensure_supported_platform
    install_locale
    enable_ros_repositories
    install_ros_jazzy
    install_ros_dev_tools
    install_project_ros_packages
    install_project_system_packages

    print_post_install_instructions
}

main "$@"