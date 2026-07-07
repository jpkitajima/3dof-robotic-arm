# 3dof-robotic-arm
Source code for a homemade 3 degrees-of-freedom robotic arm.

## Serial device access

The real servo adapter now defaults to `/dev/robot_arm_servo` instead of a hardcoded device-specific `/dev/serial/by-id/...` path.

To make that work on the supported CH340/CH341-style USB serial adapter without running as root, install the bundled `udev` rule:

```bash
./install_project.sh
```

The script:

- installs the `udev` rule in `/etc/udev/rules.d/99-robot-arm.rules`
- reloads the rules so the adapter can be picked up without logging out
- installs the project's Python dependencies from the local packages

After the script completes, unplug and replug the USB adapter once.

## Different USB hardware

The bundled `udev` rule matches the common WCH CH340/CH341 USB serial adapter family used by this project. If your hardware exposes a different USB serial chip, the rule may not create `/dev/robot_arm_servo` automatically.

In that case, launch the real adapter with an explicit path:

```bash
ros2 launch launcher robot_arm.launch.py servo_adapter_mode:=real servo_device_path:=/dev/serial/by-id/your-device
```

You can also update the rule in [udev/99-robot-arm.rules](udev/99-robot-arm.rules) for your adapter's `idVendor` and `idProduct` if you want the stable `/dev/robot_arm_servo` symlink.
