import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray

class InverseKinematics(Node):
    """
    A ROS2 node for calculating inverse kinematics for a robotic arm.
    Receives a target position in x, y, z coordinates and publishes
    the corresponding PWM values for the servos.
    """
    VERSION = 1.0

    # Constants for the robotic arm dimensions
    # for setting all angles to 0:  
    L1 = 0.1275  # Length of the first arm segment in meters
    L2 = 0.132804  # Length of the second arm segment in meters
    PEN_OFFSET = 0.02  # Offset for the pen in meters
    L3 = 0.13075  + PEN_OFFSET# Length of the third arm segment in meters

    MOTOR_2_OFFSET = 0.02183  # Offset between axis of motor 2 and axis of motor 1 in meters

    THETA_1_CHANNEL = 1
    THETA_2_CHANNEL = 2
    THETA_3_CHANNEL = 3

    THETA1_BOUNDS = (-math.pi, math.pi)
    THETA2_BOUNDS = (-math.radians(70.0), math.pi)
    THETA3_BOUNDS = (-math.pi, math.pi)

    def __init__(self):
        super().__init__('inverse_kinematics_node')

        # Elbow configuration for the 2-link plane (L2/L3):
        # - 'up'/'down': force a specific IK branch
        # - 'auto': choose a valid branch closest to the previous solution
        self.declare_parameter('elbow', 'auto')
        self._last_joint_radians: tuple[float, float, float] | None = None

        self.publisher_ = self.create_publisher(Float32MultiArray, 'st3215_angle', 1000)
        self.subscription_ = self.create_subscription(
            Float32MultiArray,
            'cartesian_xyz',
            self.cartesian_xyz_callback,
            1000
        )
        self.get_logger().info(f'Inverse Kinematics Node has been started. Version {self.VERSION}')

    @staticmethod
    def _wrap_to_pi(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi

    @classmethod
    def _angular_distance(cls, a: float, b: float) -> float:
        return abs(cls._wrap_to_pi(a - b))

    def _angles_within_bounds(self, angles: tuple[float, float, float]) -> bool:
        theta1, theta2, theta3 = angles

        if not (math.isfinite(theta1) and math.isfinite(theta2) and math.isfinite(theta3)):
            return False

        t1_min, t1_max = self.THETA1_BOUNDS
        t2_min, t2_max = self.THETA2_BOUNDS
        t3_min, t3_max = self.THETA3_BOUNDS

        return (
            (t1_min <= theta1 <= t1_max)
            and (t2_min <= theta2 <= t2_max)
            and (t3_min <= theta3 <= t3_max)
        )

    def _select_solution(
        self,
        solutions: list[tuple[float, float, float]],
        elbow_mode: str,
    ) -> tuple[float, float, float] | None:
        valid = [s for s in solutions if self._angles_within_bounds(s)]
        if not valid:
            return None

        elbow_mode = (elbow_mode or 'up').strip().lower()
        if elbow_mode in {'up', 'down'}:
            desired_sign = 1.0 if elbow_mode == 'up' else -1.0
            preferred = [s for s in valid if math.copysign(1.0, math.sin(s[2])) == desired_sign]
            return (preferred[0] if preferred else valid[0])

        # auto: prefer continuity (closest to previous joint angles)
        if self._last_joint_radians is None:
            return valid[0]

        prev = self._last_joint_radians

        def cost(sol: tuple[float, float, float]) -> float:
            return (
                self._angular_distance(sol[0], prev[0])
                + self._angular_distance(sol[1], prev[1])
                + self._angular_distance(sol[2], prev[2])
            )

        return min(valid, key=cost)

    def cartesian_xyz_callback(self, msg):
        """
        Callback function for processing received Cartesian coordinates.
        """
        self.get_logger().info(f'Received Cartesian coordinates: {msg.data}')
        if len(msg.data) != 3:
            self.get_logger().error('Invalid Cartesian coordinates received. Expected 3 values.')
            return

        x, y, z = msg.data
        self.process_coordinates(x, y, z)

    def process_coordinates(self, x: float, y: float, z: float):
        """
        Process the Cartesian coordinates and calculate the inverse kinematics.
        """
        theta1 = math.atan2(y, x)

        reachability, s, r = self.calculate_reachability(x, y, z, theta1)
        # Numerical tolerance: allow tiny overshoots from floating point error.
        if abs(reachability) > 1.0 + 1e-9:
            self.get_logger().error('Target position is out of reach.')
            return

        reachability = max(-1.0, min(1.0, reachability))

        # Two IK branches exist for theta3 (elbow-up / elbow-down)
        sin_term = math.sqrt(max(0.0, 1.0 - reachability ** 2))

        phi = math.atan2(s, r)

        solutions: list[tuple[float, float, float]] = []
        # Keep elbow-down first to match the previous single-branch behavior.
        for sign in (-1.0, 1.0):
            theta3 = math.atan2(sign * sin_term, reachability)
            psi = math.atan2(self.L3 * math.sin(theta3), self.L2 + self.L3 * math.cos(theta3))
            theta2 = phi - psi
            solutions.append((theta1, theta2, theta3))

        # For example, ros2 run robot_arm inverse_kinematics --ros-args -p elbow:=up
        elbow_mode = self.get_parameter('elbow').get_parameter_value().string_value
        chosen = self._select_solution(solutions, elbow_mode)
        if chosen is None:
            self.get_logger().error('No valid IK solution within joint bounds.')
            return

        theta1, theta2, theta3 = chosen

        self._last_joint_radians = (theta1, theta2, theta3)

        self.get_logger().info(
            f'Calculated angles (degrees): theta1={math.degrees(theta1):.3f}, theta2={math.degrees(theta2):.3f}, theta3={math.degrees(theta3):.3f}'
        )

        angles = [
            -math.degrees(theta1),
            -math.degrees(theta2),
            math.degrees(theta3)
        ]
        self.publish_angles(angles)

    def calculate_reachability(self, x: float, y: float, z: float, theta1: float):
        """
        Check if the target position is reachable by the robotic arm.
        Args:
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
            theta1 (float): Angle of the first joint
        Returns:
            tuple: (reachability metric, vertical distance, horizontal distance)
        """
        s = z - self.L1
        r = ((x + self.MOTOR_2_OFFSET*math.cos(theta1)) ** 2 + (y + self.MOTOR_2_OFFSET*math.sin(theta1)) ** 2) ** 0.5
        reachability = (r ** 2 + s ** 2 - self.L2 ** 2 - self.L3 ** 2) / (2 * self.L2 * self.L3)
        return reachability, s, r

    def publish_angles(self, angles: list[float]):
        """
        Publish the calculated angles.
        Args:
            angles (list): List of angles to publish
        """
        if len(angles) != 3:
            self.get_logger().error('Invalid angles. Expected a list of 3 values.')
            return

        channels = [self.THETA_1_CHANNEL, self.THETA_2_CHANNEL, self.THETA_3_CHANNEL]

        for channel, angle in zip(channels, angles):
            msg = Float32MultiArray()
            msg.data = [channel, angle]
            self.publisher_.publish(msg)

        self.get_logger().info(f'Published angles: {angles}')


def main(args=None):
    """
    Main function to initialize and spin the ROS2 node.
    """
    rclpy.init(args=args)
    node = InverseKinematics()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Inverse Kinematics Node.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()