# 3dof-robotic-arm
Source code for a homemade 3 degrees-of-freedom robotic arm.

## Serial device access

To allow the servo adapter to open USB serial devices without running as root, add your user to the `dialout` group:

```bash
./install_project.sh
```

The same script also installs the project's Python dependencies from the local packages.

After the script completes, log out and log back in before launching the ROS nodes.
