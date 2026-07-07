"""ROS 2 node placeholder for the real servo adapter interface.

Publishes:
- st3215_angle_read (std_msgs/Float32MultiArray)

Subscribes:
- st3215_angle (std_msgs/Float32MultiArray)
"""

from __future__ import annotations

import time

import rclpy
from serial import SerialException
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray

from python_st3215 import ST3215, ServoNotRespondingError


class ServoAdapter(Node):
    """Minimal servo adapter node scaffold with logging-only callbacks."""

    PUBLISH_PERIOD_S = 0.5
    DEFAULT_DEVICE_PATH = '/dev/robot_arm_servo'
    SERVO_IDS = (1, 2, 3)
    SERVO_RETRY_DELAY_S = 1.0
    MAX_POSITION = 4095

    def __init__(self) -> None:
        super().__init__('servo_adapter')

        self.declare_parameter('device_path', self.DEFAULT_DEVICE_PATH)
        self._device_path = str(self.get_parameter('device_path').value)

        self._controller: ST3215 | None = None
        self._servos: dict[int, object] = {}

        self._pub_read = self.create_publisher(Float32MultiArray, 'st3215_angle_read', 10)
        self._sub_angle = self.create_subscription(
            Float32MultiArray,
            'st3215_angle',
            self._on_angle_msg,
            10,
        )
        self._timer = self.create_timer(self.PUBLISH_PERIOD_S, self._publish_angle_read)

        self._connect_servo_with_retry()

        self.get_logger().info('ServoAdapter node has been started.')
        self.get_logger().info(f'Using servo device path: {self._device_path}')
        self.get_logger().info('Subscribed to st3215_angle and ready to publish st3215_angle_read.')

    def _connect_servo_with_retry(self) -> None:
        attempt = 1
        while True:
            controller: ST3215 | None = None
            servos: dict[int, object] = {}

            try:
                controller = ST3215(self._device_path)
                for servo_id in self.SERVO_IDS:
                    servo = controller.wrap_servo(servo_id)
                    current_location = servo.sram.read_current_location()
                    servos[servo_id] = servo
                    self.get_logger().info(
                        f'Connected to servo {servo_id} on {self._device_path}. '
                        f'Current location: {current_location}'
                    )
            except (OSError, SerialException, ServoNotRespondingError) as exc:
                if controller is not None:
                    controller.close()
                self.get_logger().warning(
                    f'Failed to connect to servos {self.SERVO_IDS} on attempt {attempt}: {exc}. '
                    f'Retrying in {self.SERVO_RETRY_DELAY_S:.1f}s.'
                )
                time.sleep(self.SERVO_RETRY_DELAY_S)
                attempt += 1
                continue

            self._controller = controller
            self._servos = servos
            return

    def _on_angle_msg(self, msg: Float32MultiArray) -> None:
        data = [float(value) for value in msg.data]
        if len(data) != 2:
            self.get_logger().warning(
                f'Received st3215_angle with {len(data)} values; expected exactly 2 [servo_id, angle].'
            )
            return

        servo_id = int(data[0])
        angle_deg = data[1]

        if servo_id not in self.SERVO_IDS:
            self.get_logger().warning(f'Unknown servo_id={servo_id}; ignoring.')
            return

        if servo_id not in self._servos:
            self.get_logger().warning(f'Servo {servo_id} is not connected; ignoring command.')
            return

        target_position = self._degrees_to_position(angle_deg)

        try:
            self._servos[servo_id].sram.write_target_location(target_position)
        except (OSError, SerialException, ServoNotRespondingError) as exc:
            self.get_logger().warning(
                f'Failed to write target location for servo_id={servo_id}: {exc}'
            )
            return

        self.get_logger().info(
            f'Received st3215_angle: servo_id={servo_id}, angle={angle_deg:.3f} deg, '
            f'target_position={target_position}'
        )

    def _position_to_degrees(self, position: int) -> float:
        return (float(position) / self.MAX_POSITION) * 360.0 - 180.0

    def _degrees_to_position(self, angle_deg: float) -> int:
        clamped_angle = max(-180.0, min(180.0, float(angle_deg)))
        return int(round(((clamped_angle + 180.0) / 360.0) * self.MAX_POSITION))

    def _publish_angle_read(self) -> None:
        if not self._servos:
            self.get_logger().warning('Cannot publish st3215_angle_read because no servos are connected.')
            return

        try:
            angles = [
                self._position_to_degrees(self._servos[servo_id].sram.read_current_location())
                for servo_id in self.SERVO_IDS
            ]
        except (OSError, SerialException, ServoNotRespondingError) as exc:
            self.get_logger().warning(f'Failed to read current servo locations: {exc}')
            return

        msg = Float32MultiArray()
        msg.data = angles
        self._pub_read.publish(msg)
        self.get_logger().info(f'Published st3215_angle_read: {[f"{angle:.3f}" for angle in angles]}')

    def destroy_node(self) -> bool:
        if self._controller is not None:
            self._controller.close()
            self._controller = None
            self._servos = {}

        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Entry point for the ROS 2 node."""

    rclpy.init(args=args)
    node = ServoAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()