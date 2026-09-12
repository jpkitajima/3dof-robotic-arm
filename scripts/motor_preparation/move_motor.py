"""
Simple position control - move servo to different positions.
"""

import os
import subprocess
import time
from pathlib import Path as FilePath

from python_st3215 import ST3215, ServoNotRespondingError

PATH = os.environ.get("ST3215_PATH", "/dev/robot_arm_servo")
MIN_SERVO_ID = 1
MAX_SERVO_ID = 253
MIN_TARGET_POSITION = 0
MAX_TARGET_POSITION = 4095
HALFWAY_POSITION = (MIN_TARGET_POSITION + MAX_TARGET_POSITION) // 2
UDEV_INSTALL_SCRIPT = FilePath(__file__).resolve().parents[1] / "install" / "install_udev_rule.sh"


def install_udev_rule() -> None:
    subprocess.run(["bash", str(UDEV_INSTALL_SCRIPT)], check=True)


def prompt_for_servo_id() -> int:
    response = input(
        f"Enter the motor ID to zero ({MIN_SERVO_ID}-{MAX_SERVO_ID}): "
    ).strip()

    try:
        servo_id = int(response)
    except ValueError as error:
        raise ValueError("Motor ID must be an integer.") from error

    if not MIN_SERVO_ID <= servo_id <= MAX_SERVO_ID:
        raise ValueError(
            f"Motor ID must be between {MIN_SERVO_ID} and {MAX_SERVO_ID}."
        )

    return servo_id


def prompt_for_target_position() -> int:
    response = input(
        "Enter the target position "
        f"({MIN_TARGET_POSITION}-{MAX_TARGET_POSITION}) [{HALFWAY_POSITION}]: "
    ).strip()

    if not response:
        return HALFWAY_POSITION

    try:
        target_position = int(response)
    except ValueError as error:
        raise ValueError("Target position must be an integer.") from error

    if not MIN_TARGET_POSITION <= target_position <= MAX_TARGET_POSITION:
        raise ValueError(
            "Target position must be between "
            f"{MIN_TARGET_POSITION} and {MAX_TARGET_POSITION}."
        )

    return target_position


def main() -> int:
    try:
        install_udev_rule()
    except FileNotFoundError:
        print(f"Udev install script was not found: {UDEV_INSTALL_SCRIPT}")
        return 1
    except subprocess.CalledProcessError as error:
        print(f"Udev install script failed with exit code {error.returncode}.")
        return 1

    try:
        servo_id = prompt_for_servo_id()
        target_position = prompt_for_target_position()
    except ValueError as error:
        print(error)
        return 1

    with ST3215(PATH) as controller:
        try:
            servo = controller.wrap_servo(servo_id)
        except ServoNotRespondingError:
            print(f"Servo with ID {servo_id} is not responding.")
            return 1

        servo.sram.torque_enable()

        print(f"Moving to position {target_position}...")
        servo.sram.write_target_location(target_position)
        time.sleep(5)

        servo.sram.torque_disable()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())