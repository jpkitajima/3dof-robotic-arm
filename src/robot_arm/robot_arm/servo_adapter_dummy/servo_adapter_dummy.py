"""ROS 2 dummy node that simulates the bus servo adapter interface.

Publishes:
- st3215_angle_read (std_msgs/Float32MultiArray): [0.0, 0.0, 0.0] every 5 seconds

Subscribes:
- st3215_angle (std_msgs/Float32MultiArray): logs the first three angles received
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


class ServoAdapterDummy(Node):
    """A simple publisher/subscriber node used when hardware is unavailable."""

    PUBLISH_PERIOD_S = 5.0

    def __init__(self) -> None:
        super().__init__('servo_adapter_dummy')

        self._pub_read = self.create_publisher(Float32MultiArray, 'st3215_angle_read', 10)
        self._sub_angle = self.create_subscription(
            Float32MultiArray,
            'st3215_angle',
            self._on_angle_msg,
            10,
        )
        self._timer = self.create_timer(self.PUBLISH_PERIOD_S, self._publish_dummy_read)

        self.get_logger().info('ServoAdapterDummy node has been started.')
        self.get_logger().info('Publishing st3215_angle_read every 5 seconds.')

    def _publish_dummy_read(self) -> None:
        msg = Float32MultiArray()
        msg.data = [0.0, 0.0, 0.0]
        self._pub_read.publish(msg)
        self.get_logger().info('Published st3215_angle_read: [0.0, 0.0, 0.0]')

    def _on_angle_msg(self, msg: Float32MultiArray) -> None:
        data = [float(x) for x in msg.data]
        if len(data) < 3:
            self.get_logger().warn(
                f'Received st3215_angle with {len(data)} values; expected at least 3.'
            )
            self.get_logger().info(f'Received st3215_angle raw: {data}')
            return

        angles = data[:3]
        self.get_logger().info(
            'Received st3215_angle: ' + ', '.join(f'{a:.3f}' for a in angles)
        )


def main(args: list[str] | None = None) -> None:
    """Entry point for the ROS 2 node."""

    rclpy.init(args=args)
    node = ServoAdapterDummy()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
