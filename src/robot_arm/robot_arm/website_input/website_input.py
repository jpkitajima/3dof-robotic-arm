from __future__ import annotations

import asyncio
from typing import Any

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float32MultiArray, Int32

try:
    from std_srvs.srv import Trigger
except ImportError:  # pragma: no cover
    from example_interfaces.srv import Trigger

try:
    from .state_machine import ControllerStateDispatcher, parse_controller_state
    from .utils import _resolve_resources_dir
    from .web_server import WebsiteInputWebServer
except ImportError:  # pragma: no cover
    # Allow running this file directly (outside its package) when `robot_arm` is importable.
    from robot_arm.website_input.state_machine import ControllerStateDispatcher, parse_controller_state  # type: ignore
    from robot_arm.website_input.utils import _resolve_resources_dir  # type: ignore
    from robot_arm.website_input.web_server import WebsiteInputWebServer  # type: ignore


class WebsiteInput(Node):
    """ROS2 node that hosts a small web UI and a websocket endpoint."""

    def __init__(self) -> None:
        super().__init__('website_input')

        # Match InputConverter topics/services so this virtual controller has
        # the same effect as the physical Xbox controller.
        self._pub_insert_point_manual_path = self.create_publisher(
            Float32MultiArray,
            'insert_point_manual_path',
            10,
        )

        self._pub_remove_point_manual_path = self.create_publisher(
            Int32,
            'remove_point_manual_path',
            10,
        )

        self._cli_increment_x = self.create_client(Trigger, 'increment_x')
        self._cli_decrement_x = self.create_client(Trigger, 'decrement_x')
        self._cli_increment_y = self.create_client(Trigger, 'increment_y')
        self._cli_decrement_y = self.create_client(Trigger, 'decrement_y')
        self._cli_increment_z = self.create_client(Trigger, 'increment_z')
        self._cli_decrement_z = self.create_client(Trigger, 'decrement_z')

        self._cli_turn_on_switch = self.create_client(Trigger, 'turn_on_switch')
        self._cli_turn_off_switch = self.create_client(Trigger, 'turn_off_switch')

        self._cli_start_manual_path = self.create_client(Trigger, 'start_manual_path')
        self._cli_start_drawing_circle = self.create_client(Trigger, 'start_drawing_circle')
        self._cli_start_drawing_svg = self.create_client(Trigger, 'start_drawing_svg')
        self._cli_start_drawing_line = self.create_client(Trigger, 'start_drawing_line')

        self._pending_trigger_futures: list[Any] = []
        self._last_cartesian_xyz: tuple[float, float, float] | None = None
        self._last_path_programmer_points: list[dict[str, float]] | None = None

        self._sub_cartesian_xyz_read = self.create_subscription(
            Float32MultiArray,
            'cartesian_xyz_read',
            self._on_cartesian_xyz_read,
            10,
        )

        points_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._sub_read_points_manual_path = self.create_subscription(
            Float32MultiArray,
            'read_points_manual_path',
            self._on_read_points_manual_path,
            points_qos,
        )

        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('port', 8080)

        self._host = str(self.get_parameter('host').value)
        self._port = int(self.get_parameter('port').value)

        self._static_dir = _resolve_resources_dir()

        self._dispatcher = ControllerStateDispatcher(self)

        self._web = WebsiteInputWebServer(
            host=self._host,
            port=self._port,
            static_dir=self._static_dir,
            logger=self.get_logger(),
            on_state_payload=self._on_state_payload,
            on_ws_payload=self._on_ws_payload,
            on_client_connected=self.on_client_connected,
            on_client_disconnected=self.on_client_disconnected,
            get_last_cartesian_xyz=lambda: self._last_cartesian_xyz,
            get_last_path_programmer_points=lambda: self._last_path_programmer_points,
        )

        self.get_logger().info(f'WebsiteInput ready: http://{self._host}:{self._port}/input')

def _call_trigger(self, client, service_name: str) -> None:
    if not client.service_is_ready():
        self.get_logger().warn(f'Service {service_name} not available (client not ready).')
        return

        req = Trigger.Request()
        future = client.call_async(req)
        self._pending_trigger_futures.append(future)

        def _done_cb(fut) -> None:
            try:
                result = fut.result()
                self.get_logger().info(
                    f'{service_name} -> success={getattr(result, "success", None)} '
                    f'message={getattr(result, "message", "")}'
                )
            except Exception as exc:  # noqa: BLE001
                self.get_logger().error(f'{service_name} call failed: {exc}')
            finally:
                try:
                    self._pending_trigger_futures.remove(fut)
                except ValueError:
                    pass

        future.add_done_callback(_done_cb)

    async def start(self) -> None:
        await self._web.start()

    async def stop(self) -> None:
        await self._web.stop()

    def _on_state_payload(self, payload: dict[str, Any]) -> None:
        state = parse_controller_state(payload)
        self._dispatcher.dispatch(state)

    def _on_ws_payload(self, payload: dict[str, Any]) -> None:
        msg_type = payload.get('type')
        if msg_type == 'path_programmer_start':
            self.on_path_programmer_start()
            return
        if msg_type == 'path_programmer_capture_current_position':
            self.on_path_programmer_capture_current_position()
            return
        if msg_type == 'start_drawing_circle':
            self.on_start_drawing_circle()
            return
        if msg_type == 'start_drawing_svg':
            self.on_start_drawing_svg()
            return
        if msg_type == 'start_drawing_line':
            self.on_start_drawing_line()
            return
        if msg_type == 'path_programmer_remove_point':
            index = payload.get('index')
            try:
                index_int = int(index)
            except (TypeError, ValueError):
                self.get_logger().warn(
                    f'Invalid path_programmer_remove_point index={index!r}'
                )
                return
            self.on_path_programmer_remove_point(index_int)
            return

        self.get_logger().debug(f'Ignoring websocket message type={msg_type!r}')

    # --- Handler methods (fill these in later) ---

    def on_client_connected(self, peer: str | None) -> None:
        self.get_logger().info(f'Web client connected: {peer}')

    def on_client_disconnected(self, peer: str | None) -> None:
        self.get_logger().info(f'Web client disconnected: {peer}')

    def on_path_programmer_start(self) -> None:
        self.get_logger().info('Path Programmer: start received')
        self._call_trigger(self._cli_start_manual_path, 'start_manual_path')
        return

    def on_path_programmer_capture_current_position(self) -> None:
        last = self._last_cartesian_xyz
        if last is None:
            self.get_logger().warn(
                'Path Programmer: capture current position received but no cartesian_xyz_read yet'
            )
            return

        x, y, z = last

        msg = Float32MultiArray()
        # PointsManager expects [index, x, y, z]. index=-1 appends.
        msg.data = [-1.0, float(x), float(y), float(z)]
        self._pub_insert_point_manual_path.publish(msg)
        self.get_logger().info(
            f'Path Programmer: captured point appended (x={x:.3f}, y={y:.3f}, z={z:.3f})'
        )
        return

    def on_path_programmer_remove_point(self, index: int) -> None:
        if index < 0:
            self.get_logger().warn(
                f'Path Programmer: remove point received with negative index={index}'
            )
            return

        msg = Int32()
        msg.data = int(index)
        self._pub_remove_point_manual_path.publish(msg)
        self.get_logger().info(
            f'Path Programmer: remove point published to remove_point_manual_path (index={index})'
        )
        return

    def on_start_drawing_circle(self) -> None:
        self.get_logger().info('Website action: start drawing circle received')
        self._call_trigger(self._cli_start_drawing_circle, 'start_drawing_circle')

    def on_start_drawing_svg(self) -> None:
        self.get_logger().info('Website action: start drawing svg received')
        self._call_trigger(self._cli_start_drawing_svg, 'start_drawing_svg')

    def on_start_drawing_line(self) -> None:
        self.get_logger().info('Website action: start drawing line received')
        self._call_trigger(self._cli_start_drawing_line, 'start_drawing_line')

    def on_lb(self, pressed: bool) -> None:
        if pressed:
            self._call_trigger(self._cli_increment_z, 'increment_z')

    def on_rb(self, pressed: bool) -> None:
        if pressed:
            self._call_trigger(self._cli_decrement_z, 'decrement_z')

    def on_a(self, pressed: bool) -> None:
        if pressed:
            self._call_trigger(self._cli_decrement_x, 'decrement_x')

    def on_b(self, pressed: bool) -> None:
        if pressed:
            self._call_trigger(self._cli_decrement_y, 'decrement_y')

    def on_x(self, pressed: bool) -> None:
        if pressed:
            self._call_trigger(self._cli_increment_y, 'increment_y')

    def on_y(self, pressed: bool) -> None:
        if pressed:
            self._call_trigger(self._cli_increment_x, 'increment_x')

    def on_switch_on(self, pressed: bool) -> None:
        if pressed:
            self._call_trigger(self._cli_turn_on_switch, 'turn_on_switch')

    def on_switch_off(self, pressed: bool) -> None:
        if pressed:
            self._call_trigger(self._cli_turn_off_switch, 'turn_off_switch')

    def _on_cartesian_xyz_read(self, msg: Float32MultiArray) -> None:
        data = list(msg.data)
        if len(data) < 3:
            self.get_logger().warn(
                f'Invalid cartesian_xyz_read received. Expected 3 values, got {len(data)}.'
            )
            return

        x, y, z = float(data[0]), float(data[1]), float(data[2])
        self._last_cartesian_xyz = (x, y, z)

        asyncio.create_task(
            self._web.broadcast_json(
                {
                    'type': 'cartesian_xyz_read',
                    'x': x,
                    'y': y,
                    'z': z,
                }
            )
        )

    def _on_read_points_manual_path(self, msg: Float32MultiArray) -> None:
        data = list(msg.data)
        if len(data) % 3 != 0:
            self.get_logger().warn(
                'Invalid read_points_manual_path received. Expected multiple of 3 values, '
                f'got {len(data)}.'
            )

        points: list[dict[str, float]] = []
        for i in range(0, len(data) - 2, 3):
            x = float(data[i])
            y = float(data[i + 1])
            z = float(data[i + 2])
            points.append({'x': x, 'y': y, 'z': z})

        # Cache for new websocket clients that connect after the last broadcast.
        self._last_path_programmer_points = points

        asyncio.create_task(
            self._web.broadcast_json(
                {
                    'type': 'path_programmer_points',
                    'points': points,
                }
            )
        )


async def _async_main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = WebsiteInput()

    try:
        await node.start()

        # Main loop: let aiohttp run, and keep ROS responsive.
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            await asyncio.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            await node.stop()
        finally:
            node.destroy_node()
            rclpy.shutdown()


def main(args: list[str] | None = None) -> None:
    asyncio.run(_async_main(args=args))


if __name__ == '__main__':
    main()
