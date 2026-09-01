import subprocess
import time
from pathlib import Path
from typing import Optional

from python_st3215 import ST3215, ServoNotRespondingError


DEVICE_PATH = "/dev/robot_arm_servo"
MIN_SERVO_ID = 1
MAX_SERVO_ID = 253
UDEV_INSTALL_SCRIPT = Path(__file__).resolve().parents[1] / "install" / "install_udev_rule.sh"


def install_udev_rule() -> None:
    subprocess.run(
        ["bash", str(UDEV_INSTALL_SCRIPT)],
        check=True,
    )


def find_servo_id(controller: ST3215) -> Optional[int]:
    print("Scanning for servos...")

    for servo_id in range(MIN_SERVO_ID, MAX_SERVO_ID + 1):
        try:
            controller.wrap_servo(servo_id)
            print(f"Found servo with ID {servo_id}")
            return servo_id
        except ServoNotRespondingError:
            continue

    return None


def prompt_for_new_id(current_id: int) -> int:
    response = input(
        f"Current ID is {current_id}. Enter a new ID ({MIN_SERVO_ID}-{MAX_SERVO_ID}): "
    ).strip()

    try:
        new_id = int(response)
    except ValueError as error:
        raise ValueError("New ID must be an integer.") from error

    if not MIN_SERVO_ID <= new_id <= MAX_SERVO_ID:
        raise ValueError(f"New ID must be between {MIN_SERVO_ID} and {MAX_SERVO_ID}.")

    if new_id == current_id:
        raise ValueError("New ID must differ from the current ID.")

    return new_id


def change_servo_id(controller: ST3215, old_id: int, new_id: int) -> bool:
    with controller:
        servo = controller.wrap_servo(old_id)
        servo.sram.unlock()

        try:
            print(f"Writing new ID {new_id}...")
            servo.eeprom.write_id(new_id)
        finally:
            servo.sram.lock()

        time.sleep(1)

        updated_servo = controller.wrap_servo(new_id)
        confirmed_id = updated_servo.eeprom.read_id()

    if confirmed_id == new_id:
        print(f"Successfully changed to ID {new_id}")
        return True

    print(f"Failed to change ID (read back: {confirmed_id})")
    return False


def main() -> int:
    try:
        install_udev_rule()
    except FileNotFoundError:
        print(f"Udev install script was not found: {UDEV_INSTALL_SCRIPT}")
        return 1
    except subprocess.CalledProcessError as error:
        print(f"Udev install script failed with exit code {error.returncode}.")
        return 1

    controller = ST3215(DEVICE_PATH)
    current_id = find_servo_id(controller)

    if current_id is None:
        print("No servo found on the bus.")
        return 1

    try:
        new_id = prompt_for_new_id(current_id)
    except ValueError as error:
        print(error)
        return 1

    return 0 if change_servo_id(controller, current_id, new_id) else 1


if __name__ == "__main__":
    raise SystemExit(main())
