# 3dof-robotic-arm
Source code for a homemade 3 degrees-of-freedom robotic arm.

## Serial device access

To allow the servo adapter to open the robot arm USB serial device without running as root, install the generated `udev` rule:

```bash
./install_project.sh
```

The same script also installs the project's Python dependencies from the local packages.

If the device is not auto-detected or you have multiple serial devices connected, pass the target path explicitly:

```bash
./install_project.sh /dev/ttyACM0
```

To install or refresh only the `udev` rule, use:

```bash
./install_udev_rule.sh /dev/ttyACM0
```

After the script completes, replug the robot arm if device access does not update immediately.
