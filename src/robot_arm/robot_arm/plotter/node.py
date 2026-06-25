from __future__ import annotations

from pathlib import Path
from time import sleep

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

try:
    from std_srvs.srv import Trigger
except ImportError:  # pragma: no cover
    from example_interfaces.srv import Trigger

from ament_index_python.packages import get_package_share_directory
from std_msgs.msg import Float32MultiArray

from .circle import CirclePointGenerator
from .config import PlotterParams
from .motion import MotionPlanner
from .svg import SvgPointGenerator


class RobotArmPlotterNode(Node):
    """ROS2 node that publishes Cartesian points for the robot arm to follow."""

    def __init__(self, params: PlotterParams | None = None):
        super().__init__("robot_arm_plotter")
        self.get_logger().info("Initializing RobotArmPlotterNode...")
        self.params = params or PlotterParams()

        self.declare_parameter('manual_path_step', 0.001)
        self.declare_parameter('manual_path_delay', 0.2)

        self._manual_path_points: list[tuple[float, float, float]] = []

        self._circle_gen = CirclePointGenerator()
        self._svg_gen = SvgPointGenerator()

        self.publisher_ = self.create_publisher(Float32MultiArray, "cartesian_xyz", 1000)

        points_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            Float32MultiArray,
            'read_points_manual_path',
            self._on_read_points_manual_path,
            points_qos,
        )

        self.create_service(Trigger, "start_drawing_circle", self.handle_start_drawing_circle)
        self.create_service(Trigger, "start_drawing_svg", self.handle_start_drawing_svg)
        self.create_service(Trigger, "start_drawing_line", self.handle_start_drawing_line)
        self.create_service(Trigger, 'start_manual_path', self.handle_start_manual_path)
        self.create_service(Trigger, "turn_on_switch", self.handle_turn_on_switch)
        self.create_service(Trigger, "turn_off_switch", self.handle_turn_off_switch)

    def _on_read_points_manual_path(self, msg: Float32MultiArray) -> None:
        data = list(msg.data)
        if len(data) % 3 != 0:
            self.get_logger().warn(
                'Invalid read_points_manual_path received. Expected multiple of 3 values, '
                f'got {len(data)}.'
            )

        points: list[tuple[float, float, float]] = []
        for i in range(0, len(data) - 2, 3):
            points.append((float(data[i]), float(data[i + 1]), float(data[i + 2])))

        self._manual_path_points = points

    def handle_start_manual_path(self, request, response):
        self.get_logger().info('Received request to start manual path.')

        if not self._manual_path_points:
            response.success = False
            response.message = (
                'No manual path points available. '
                'Waiting for read_points_manual_path to publish.'
            )
            return response

        step = float(self.get_parameter('manual_path_step').value)
        delay = float(self.get_parameter('manual_path_delay').value)

        points: list[Float32MultiArray] = []
        if len(self._manual_path_points) == 1:
            msg = Float32MultiArray()
            x, y, z = self._manual_path_points[0]
            msg.data = [float(x), float(y), float(z)]
            points.append(msg)
        else:
            for i in range(len(self._manual_path_points) - 1):
                MotionPlanner.append_linear_motion(
                    points,
                    self._manual_path_points[i],
                    self._manual_path_points[i + 1],
                    step,
                )
                # Avoid duplicating the waypoint at segment boundaries.
                if i != len(self._manual_path_points) - 2 and points:
                    points.pop()

        self._publish_points(points, delay)

        response.success = True
        response.message = f'Manual path complete. Published {len(points)} points.'
        return response

    def handle_turn_on_switch(self, request, response):
        self.get_logger().info("Received request to turn on switch.")

        points: list[Float32MultiArray] = []
        MotionPlanner.append_linear_motion(
            points,
            self.params.rest_position,
            self.params.switch_on_position,
            self.params.retraction_step,
        )
        MotionPlanner.append_linear_motion(
            points,
            self.params.switch_on_position,
            self.params.rest_position,
            self.params.retraction_step,
        )
        self._publish_points(points, self.params.delay)

        response.success = True
        response.message = "Switch on motion complete."
        return response

    def handle_turn_off_switch(self, request, response):
        self.get_logger().info("Received request to turn off switch.")

        points: list[Float32MultiArray] = []
        MotionPlanner.append_linear_motion(
            points,
            self.params.rest_position,
            self.params.switch_off_position,
            self.params.retraction_step,
        )
        MotionPlanner.append_linear_motion(
            points,
            self.params.switch_off_position,
            self.params.rest_position,
            self.params.retraction_step,
        )
        self._publish_points(points, self.params.delay)

        response.success = True
        response.message = "Switch off motion complete."
        return response

    def handle_start_drawing_line(self, request, response):
        self.get_logger().info("Received request to start drawing a line.")
        start_xyz = (0.22, 0.0, 0.0)
        end_xyz = (0.02, 0.0, 0.0)

        points_forward = MotionPlanner.generate_line_points(
            start_xyz,
            end_xyz,
            num_points_in_between=100,
        )
        points_backward = MotionPlanner.generate_line_points(
            end_xyz,
            start_xyz,
            num_points_in_between=100,
        )
        points = points_forward + points_backward[1:]

        self._publish_points(points, 0.1)
        response.success = True
        response.message = "Line drawing complete."
        return response

    def handle_start_drawing_circle(self, request, response):
        self.get_logger().info("Received request to start drawing a circle.")
        points = self._circle_gen.generate(
            self.params.circle_center,
            self.params.radius,
            self.params.num_points,
        )
        self._publish_points(points, self.params.delay)

        response.success = True
        response.message = "Circle drawing complete."
        return response

    def handle_start_drawing_svg(self, request, response):
        self.get_logger().info("Received request to start drawing from SVG.")
        try:
            svg_path = self._get_svg_path()
            points = self._svg_gen.generate(
                svg_path=svg_path,
                borders=self.params.art_borders,
                rest_position=self.params.rest_position,
                retraction_distance=self.params.retraction_distance,
                retraction_step=self.params.retraction_step,
            )
            self._publish_points(points, self.params.art_delay)
            response.success = True
            response.message = "SVG drawing complete."
        except Exception as exc:
            self.get_logger().error(f"Failed to process SVG: {exc}")
            response.success = False
            response.message = f"Error: {exc}"
        return response

    def _get_svg_path(self) -> str:
        name = self.params.svg_resource_name

        # Prefer installed resources.
        package_share_dir = Path(get_package_share_directory("robot_arm"))
        candidate = package_share_dir / "resource" / "plotter" / name
        if candidate.is_file():
            return str(candidate)

        # Legacy installed layout.
        candidate = package_share_dir / "resource" / name
        if candidate.is_file():
            return str(candidate)

        # Workspace/source fallback.
        candidate = Path(__file__).resolve().parent / "resources" / name
        return str(candidate)

    def _publish_points(self, points: list[Float32MultiArray], delay: float) -> None:
        for point in points:
            self.publisher_.publish(point)
            sleep(delay)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RobotArmPlotterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
