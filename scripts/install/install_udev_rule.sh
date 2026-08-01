#!/usr/bin/env bash

set -euo pipefail

rule_path="/etc/udev/rules.d/99-robot-arm.rules"
script_name="$(basename "${BASH_SOURCE[0]}")"
sudo_cmd=()

usage() {
    cat <<EOF
Usage: ./${script_name} [/dev/ttyACM0|/dev/ttyUSB0]

Installs a udev rule for the robot arm serial device using TAG+="uaccess"
so the active local user can open the device without dialout membership.

If no device path is provided, the script auto-detects a single connected
serial TTY from /dev/ttyACM* or /dev/ttyUSB*.
EOF
}

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

detect_device_path() {
    local candidates=()
    local tty_path

    for tty_path in /dev/ttyACM* /dev/ttyUSB*; do
        if [[ -e "$tty_path" ]]; then
            candidates+=("$tty_path")
        fi
    done

    if (( ${#candidates[@]} == 0 )); then
        echo "No serial TTY device found under /dev/ttyACM* or /dev/ttyUSB*." >&2
        exit 1
    fi

    if (( ${#candidates[@]} > 1 )); then
        echo "Multiple serial TTY devices found. Pass the target device path explicitly:" >&2
        printf '  %s\n' "${candidates[@]}" >&2
        exit 1
    fi

    printf '%s\n' "${candidates[0]}"
}

extract_udev_attribute() {
    local device_path="$1"
    local attr_name="$2"

    udevadm info -a -n "$device_path" | awk -F '=="' -v name="$attr_name" '
        $0 ~ "ATTRS\\{" name "\\}" {
            split($2, parts, "\"")
            print parts[1]
            exit
        }
    '
}

write_rule() {
    local id_vendor="$1"
    local id_product="$2"
    local rule_line

    rule_line="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"$id_vendor\", ATTRS{idProduct}==\"$id_product\", TAG+=\"uaccess\", SYMLINK+=\"robot_arm_servo\""

    echo "Writing udev rule to $rule_path"
    printf '%s\n' "$rule_line" | "${sudo_cmd[@]}" tee "$rule_path" >/dev/null
}

write_reload_and_trigger_rules_twice() {
    local device_path="$1"
    local id_vendor="$2"
    local id_product="$3"
    local device_name
    local pass

    device_name="$(basename "$device_path")"

    for pass in 1 2; do
        write_rule "$id_vendor" "$id_product"
        "${sudo_cmd[@]}" udevadm control --reload-rules
        "${sudo_cmd[@]}" udevadm trigger --action=add --name-match="$device_name"
    done
}

wait_for_device_access() {
    local device_path="$1"
    local attempt
    local max_attempts=10

    for attempt in $(seq 1 "$max_attempts"); do
        if [[ -e "$device_path" && -r "$device_path" && -w "$device_path" ]]; then
            return 0
        fi

        sleep 1
    done

    return 1
}

main() {
    local device_path="${1:-}"
    local id_vendor
    local id_product

    if [[ "$device_path" == "-h" || "$device_path" == "--help" ]]; then
        usage
        exit 0
    fi

    require_command udevadm
    init_privilege_command

    if [[ -z "$device_path" ]]; then
        device_path="$(detect_device_path)"
    fi

    echo "Using serial device path: $device_path"

    if [[ ! -e "$device_path" ]]; then
        echo "Device path '$device_path' does not exist." >&2
        exit 1
    fi

    id_vendor="$(extract_udev_attribute "$device_path" idVendor)"
    id_product="$(extract_udev_attribute "$device_path" idProduct)"

    if [[ -z "$id_vendor" || -z "$id_product" ]]; then
        echo "Failed to extract idVendor/idProduct for '$device_path'." >&2
        exit 1
    fi

    echo "Using USB IDs: idVendor=$id_vendor, idProduct=$id_product"

    echo "Reloading udev rules..."
    write_reload_and_trigger_rules_twice "$device_path" "$id_vendor" "$id_product"
    

    if ! wait_for_device_access "/dev/robot_arm_servo"; then
        echo "Warning: /dev/robot_arm_servo is not readable and writable yet." >&2
        echo "Replug the device if access does not update immediately." >&2
    fi

    echo "Installed udev rule for $device_path"
    echo "Matched attributes: idVendor=$id_vendor, idProduct=$id_product"
}

main "$@"