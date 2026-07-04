"""ROS 2 dummy node that simulates the bus servo adapter interface.

Publishes:
- st3215_angle_read (std_msgs/Float32MultiArray): [0.0, 0.0, 0.0] every 0.5 seconds
- /joint_states (sensor_msgs/JointState): current joint angles for RViz visualization

Subscribes:
- st3215_angle (std_msgs/Float32MultiArray): [servo_id, angle] — motor ID and target angle in degrees
"""

from __future__ import annotations

import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float32MultiArray


class ServoAdapterDummy(Node):
    """A simple publisher/subscriber node used when hardware is unavailable."""

    PUBLISH_PERIOD_S = 0.5

    SERVO_ID_TO_JOINT = {
        1: 'base_to_link1',
        2: 'link1_to_link2',
        3: 'link2_to_link3',
    }

    def __init__(self) -> None:
        super().__init__('servo_adapter_dummy')

        self._joint_angles: dict[str, float] = {name: 0.0 for name in self.SERVO_ID_TO_JOINT.values()}

        self._pub_read = self.create_publisher(Float32MultiArray, 'st3215_angle_read', 10)
        self._pub_joint_states = self.create_publisher(JointState, '/joint_states', 10)
        self._sub_angle = self.create_subscription(
            Float32MultiArray,
            'st3215_angle',
            self._on_angle_msg,
            10,
        )
        self._timer = self.create_timer(self.PUBLISH_PERIOD_S, self._publish_dummy_read)

        self.get_logger().info('ServoAdapterDummy node has been started.')
        self.get_logger().info(
            f'Publishing st3215_angle_read every {self.PUBLISH_PERIOD_S:.1f} seconds.'
        )
    def _publish_dummy_read(self) -> None:
        angles_deg = [math.degrees(self._joint_angles[name]) for name in self.SERVO_ID_TO_JOINT.values()]
        msg = Float32MultiArray()
        msg.data = angles_deg
        self._pub_read.publish(msg)
        self.get_logger().info(f'Published st3215_angle_read: {[f"{a:.3f}" for a in angles_deg]}')

        self._publish_joint_states()

    def _publish_joint_states(self) -> None:
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = list(self._joint_angles.keys())
        js.position = list(self._joint_angles.values())
        self._pub_joint_states.publish(js)

    def _on_angle_msg(self, msg: Float32MultiArray) -> None:
        data = [float(x) for x in msg.data]
        if len(data) != 2:
            self.get_logger().warn(
                f'Received st3215_angle with {len(data)} values; expected exactly 2 [servo_id, angle].'
            )
            return

        servo_id = int(data[0])
        angle_deg = data[1]

        joint_name = self.SERVO_ID_TO_JOINT.get(servo_id)
        if joint_name is None:
            self.get_logger().warn(f'Unknown servo_id={servo_id}; ignoring.')
            return

        self._joint_angles[joint_name] = math.radians(angle_deg)
        self.get_logger().info(
            f'Received st3215_angle: servo_id={servo_id} ({joint_name}), angle={angle_deg:.3f} deg'
        )

        self._publish_joint_states()


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
