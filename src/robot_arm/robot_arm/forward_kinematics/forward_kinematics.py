import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


class ForwardKinematics(Node):
    """Forward-kinematics node for a 3DOF arm.

    Subscribes to `st3215_angle_read` with `[theta1, theta2, theta3]` and publishes
    `cartesian_xyz_read` with `[x, y, z]`.

    Notes on equations:
    - theta1 is the base yaw, so it should not affect z.
    - In the standard 2-link planar model used by this repo's IK node, the planar radius is:
        r = L2*cos(theta2) + L3*cos(theta2 + theta3)
      and the vertical offset is:
        s = L2*sin(theta2) + L3*sin(theta2 + theta3)
      so:
        z = L1 + s
        x = (r - motor2_offset)*cos(theta1)
        y = (r - motor2_offset)*sin(theta1)

    The `motor2_offset` term matches the inverse kinematics node, which uses an offset between
    the axis of motor 1 and motor 2 when computing r.
    """

    VERSION = 1.0

    # Link lengths (meters). Matches `robot_arm.inverse_kinematics.inverse_kinematics.InverseKinematics`.
    L1 = 0.1275
    L2 = 0.132804
    PEN_OFFSET = 0.02
    L3 = 0.13075 + PEN_OFFSET

    # Offset between axis of motor 1 and axis of motor 2 (meters).
    MOTOR_2_OFFSET = 0.02183

    def __init__(self) -> None:
        super().__init__('forward_kinematics_node')

        self._pub_xyz = self.create_publisher(Float32MultiArray, 'cartesian_xyz_read', 1000)
        self._sub_angles = self.create_subscription(
            Float32MultiArray,
            'st3215_angle_read',
            self._on_angles,
            1000,
        )

        self.get_logger().info(f'Forward Kinematics Node started. Version {self.VERSION}')

    def _on_angles(self, msg: Float32MultiArray) -> None:
        data = list(msg.data)
        if len(data) != 3:
            self.get_logger().error(
                f'Invalid st3215_angle_read received. Expected 3 values, got {len(data)}.'
            )
            return

        theta1_in, theta2_in, theta3_in = (float(data[0]), float(data[1]), float(data[2]))
        x, y, z = self._forward_kinematics(theta1_in, theta2_in, theta3_in)

        self.get_logger().info(f'Received angles (degrees): [{theta1_in}, {theta2_in}, {theta3_in}] -> '
                               f'Computed position (meters): [{x}, {y}, {z}]')

        out = Float32MultiArray()
        out.data = [float(x), float(y), float(z)]
        self._pub_xyz.publish(out)

    def _forward_kinematics(self, theta1: float, theta2: float, theta3: float) -> tuple[float, float, float]:
        # Assumption: input angles are always in degrees.
        t1 = math.radians(-theta1)
        t2 = math.radians(-theta2)
        t3 = math.radians(theta3)

        # Standard planar FK for the 2-link arm in the (r, z) plane
        r_plane = (self.L2 * math.cos(t2)) + (self.L3 * math.cos(t2 + t3))
        z = self.L1 + (self.L2 * math.sin(t2)) + (self.L3 * math.sin(t2 + t3))

        # Convert planar r into world x/y, consistent with the IK node's motor-2 offset model.
        r_from_motor1_axis = r_plane - self.MOTOR_2_OFFSET
        x = math.cos(t1) * r_from_motor1_axis
        y = math.sin(t1) * r_from_motor1_axis

        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            self.get_logger().warn(
                f'Computed non-finite FK result for angles [{theta1}, {theta2}, {theta3}] (degrees).'
            )

        return x, y, z


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ForwardKinematics()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Forward Kinematics Node.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
