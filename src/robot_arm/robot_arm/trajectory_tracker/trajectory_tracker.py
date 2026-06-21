import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import Float32MultiArray, ColorRGBA
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker


class TrajectoryTracker(Node):
    """Draws the end-effector trajectory in RViz as a LINE_STRIP marker.

    Subscribes to ``cartesian_xyz_read`` (Float32MultiArray [x, y, z]) published
    by the forward-kinematics node and republishes an accumulating
    ``visualization_msgs/Marker`` on ``/trajectory_marker``.

    A ``/clear_trajectory`` service (std_srvs/Trigger) wipes the stored path.
    """

    VERSION = 1.0

    # Minimum distance (meters) between consecutive stored points to avoid
    # flooding the marker with nearly-identical poses.
    MIN_DISTANCE = 0.001

    def __init__(self) -> None:
        super().__init__('trajectory_tracker')

        self._current_segment: list[Point] = []  # points in the active (pen-down) stroke
        self._committed_count: int = 0           # number of frozen strokes already published
        self._pen_was_down: bool = False

        self.declare_parameter('marker_frame', 'base_link')

        self._pub = self.create_publisher(Marker, '/trajectory_marker', 10)

        self.create_subscription(
            Float32MultiArray,
            'cartesian_xyz_read',
            self._on_xyz,
            1000,
        )

        self.create_service(Trigger, 'clear_trajectory', self._on_clear)

        self.get_logger().info(f'TrajectoryTracker started (v{self.VERSION}).')

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_xyz(self, msg: Float32MultiArray) -> None:
        data = list(msg.data)
        if len(data) != 3:
            self.get_logger().warn(
                f'Expected 3 floats on cartesian_xyz_read, got {len(data)}. Skipping.'
            )
            return

        self.get_logger().info(
            f'Received: x={float(data[0]):.4f}  y={float(data[1]):.4f}  z={float(data[2]):.4f}'
        )

        pen_down = abs(float(data[0]) - 0.2) <= 1e-4

        if pen_down:
            factor = 10
            p = Point(x=-float(data[0] * factor), y=float(data[1] * factor), z=float(data[2] * factor))

            # Skip nearly-identical consecutive points
            if self._current_segment:
                last = self._current_segment[-1]
                dist = ((p.x - last.x) ** 2 + (p.y - last.y) ** 2 + (p.z - last.z) ** 2) ** 0.5
                if dist < self.MIN_DISTANCE:
                    self._pen_was_down = pen_down
                    return

            self._current_segment.append(p)
            self.get_logger().info(
                f'Stroke {self._committed_count} point #{len(self._current_segment)}: '
                f'x={p.x:.4f}  y={p.y:.4f}  z={p.z:.4f}'
            )
            self._publish_segment(self._committed_count, self._current_segment)
        else:
            # Pen lifted: freeze the current stroke and start a new one
            if self._pen_was_down and self._current_segment:
                self.get_logger().info(
                    f'Pen lifted — committing stroke {self._committed_count} '
                    f'({len(self._current_segment)} points).'
                )
                self._committed_count += 1
                self._current_segment = []

        self._pen_was_down = pen_down

    def _on_clear(self, _request, response):
        self._current_segment = []
        self._committed_count = 0
        self._pen_was_down = False
        # DELETEALL removes every marker in the namespace
        frame = self.get_parameter('marker_frame').get_parameter_value().string_value
        marker = Marker()
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.header.frame_id = frame
        marker.ns = 'trajectory'
        marker.action = Marker.DELETEALL
        self._pub.publish(marker)
        response.success = True
        response.message = 'Trajectory cleared.'
        self.get_logger().info('Trajectory cleared.')
        return response

    # ------------------------------------------------------------------
    # Marker publishing
    # ------------------------------------------------------------------

    def _publish_segment(self, segment_id: int, points: list[Point]) -> None:
        frame = self.get_parameter('marker_frame').get_parameter_value().string_value
        marker = Marker()
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.header.frame_id = frame
        marker.ns = 'trajectory'
        marker.id = segment_id
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        marker.scale.x = 0.02
        marker.scale.y = 0.02
        marker.scale.z = 0.02
        marker.color = ColorRGBA(r=1.0, g=0.4, b=0.0, a=1.0)
        if len(points) >= 2:
            marker.points = list(points)
        self._pub.publish(marker)


def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
