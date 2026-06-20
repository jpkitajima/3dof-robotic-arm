from __future__ import annotations

from dataclasses import dataclass

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray

try:
    from std_srvs.srv import Trigger
except ImportError:  # pragma: no cover
    from example_interfaces.srv import Trigger


@dataclass
class CartesianXYZ:
    x: float
    y: float
    z: float


class InputReceiver(Node):
    """Small command node for nudging a target Cartesian point.

    - Subscribes: `cartesian_xyz_read` (Float32MultiArray [x, y, z])
    - Publishes: `cartesian_xyz` (Float32MultiArray [x, y, z])
        - Services (Trigger):
            increment_x, decrement_x, increment_y, decrement_y, increment_z, decrement_z

    The node keeps the latest measured (x, y, z) from `cartesian_xyz_read` and, when a
    service is called, applies a configurable step to the corresponding coordinate and
    publishes the new target to `cartesian_xyz` (consumed by the IK node).
    """

    VERSION = 1.0

    STEP_METERS = 0.01
    XYZ_READ_TOPIC = 'cartesian_xyz_read'
    XYZ_TOPIC = 'cartesian_xyz'

    def __init__(self) -> None:
        super().__init__('input_receiver_node')

        self._step = float(self.STEP_METERS)
        self._xyz_read_topic = self.XYZ_READ_TOPIC
        self._xyz_topic = self.XYZ_TOPIC

        self._xyz: CartesianXYZ | None = None

        self._sub_xyz_read = self.create_subscription(
            Float32MultiArray,
            self._xyz_read_topic,
            self._on_xyz_read,
            1000,
        )
        self._pub_xyz = self.create_publisher(Float32MultiArray, self._xyz_topic, 1000)

        self.create_service(Trigger, 'increment_x', self._handle_increment_x)
        self.create_service(Trigger, 'decrement_x', self._handle_decrement_x)
        self.create_service(Trigger, 'increment_y', self._handle_increment_y)
        self.create_service(Trigger, 'decrement_y', self._handle_decrement_y)
        self.create_service(Trigger, 'increment_z', self._handle_increment_z)
        self.create_service(Trigger, 'decrement_z', self._handle_decrement_z)

        self.get_logger().info(
            f'InputReceiver started. Version {self.VERSION}. '
            f'step={self._step}m read={self._xyz_read_topic} write={self._xyz_topic}'
        )

    def _on_xyz_read(self, msg: Float32MultiArray) -> None:
        data = list(msg.data)
        if len(data) != 3:
            self.get_logger().warn(
                f'Invalid cartesian_xyz_read received. Expected 3 values, got {len(data)}.'
            )
            return

        x, y, z = (float(data[0]), float(data[1]), float(data[2]))
        self._xyz = CartesianXYZ(x=x, y=y, z=z)

    def _publish_target(self, xyz: CartesianXYZ) -> None:
        msg = Float32MultiArray()
        msg.data = [float(xyz.x), float(xyz.y), float(xyz.z)]
        self._pub_xyz.publish(msg)

    def _apply_delta(
        self,
        dx: float,
        dy: float,
        dz: float,
        response: Trigger.Response,
    ) -> Trigger.Response:
        if self._xyz is None:
            response.success = False
            response.message = (
                f'No current pose yet (waiting for {self._xyz_read_topic}). '
                'Try again once cartesian_xyz_read is publishing.'
            )
            return response

        new_xyz = CartesianXYZ(
            x=self._xyz.x + float(dx),
            y=self._xyz.y + float(dy),
            z=self._xyz.z + float(dz),
        )
        self._publish_target(new_xyz)

        # Update our local value immediately to reflect what we just commanded.
        # FK will later overwrite this with the measured pose.
        self._xyz = new_xyz

        response.success = True
        response.message = (
            f'Published target [{new_xyz.x:.5f}, {new_xyz.y:.5f}, {new_xyz.z:.5f}]'
        )
        return response

    def _handle_increment_x(
        self,
        _request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        return self._apply_delta(self._step, 0.0, 0.0, response)

    def _handle_decrement_x(
        self,
        _request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        return self._apply_delta(-self._step, 0.0, 0.0, response)

    def _handle_increment_y(
        self,
        _request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        return self._apply_delta(0.0, self._step, 0.0, response)

    def _handle_decrement_y(
        self,
        _request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        return self._apply_delta(0.0, -self._step, 0.0, response)

    def _handle_increment_z(
        self,
        _request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        return self._apply_delta(0.0, 0.0, self._step, response)

    def _handle_decrement_z(
        self,
        _request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        return self._apply_delta(0.0, 0.0, -self._step, response)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = InputReceiver()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down InputReceiver.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
