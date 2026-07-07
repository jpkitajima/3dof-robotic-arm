"""Persistent point-list manager.

This node keeps an in-memory list of 3D points (x, y, z) and persists it to a
YAML file on disk.

Because the surrounding `robot_arm` package is an `ament_python` package (no
custom ROS interface generation), this node exposes its interface using
standard message/service types:

- Subscribed topics:
    - `~/insert_point_manual_path` (std_msgs/msg/Float32MultiArray): [index, x, y, z]
    - index == -1 (or index >= len) appends.
    - 0 <= index <= len inserts at that position.
    - `~/remove_point_manual_path` (std_msgs/msg/Int32): index to remove.

- Published topics:
    - `~/read_points_manual_path` (std_msgs/msg/Float32MultiArray): flattened [x, y, z, ...]

Parameters:
  - `storage_path` (string): where to persist YAML. Default:
      $ROS_HOME/robot_arm/points.yaml (or ~/.ros/robot_arm/points.yaml)
  - `auto_save` (bool): save to disk after each change. Default: true.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import tempfile
import threading
from typing import Any

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float32MultiArray, Int32

try:
    import yaml
except Exception as exc:  # pragma: no cover
    yaml = None
    _yaml_import_error = exc


@dataclass(frozen=True)
class Point3:
    """Simple 3D point container."""

    x: float
    y: float
    z: float


def _default_storage_path() -> str:
    ros_home = os.environ.get('ROS_HOME')
    base = Path(ros_home).expanduser() if ros_home else Path.home() / '.ros'
    return str(base / 'robot_arm' / 'points.yaml')


class PointsManager(Node):
    """ROS 2 node that persists and manages an ordered list of points."""

    def __init__(self) -> None:
        super().__init__('points_manager')

        self.declare_parameter('storage_path', _default_storage_path())
        self.declare_parameter('auto_save', True)

        if yaml is None:
            raise RuntimeError(
                'PyYAML is required for robot_arm.manual_path_programmer.points_manager '
                f'but could not be imported: {_yaml_import_error}'
            )

        self._lock = threading.Lock()
        self._points: list[Point3] = []

        # Transient-local makes this topic behave like a latched publisher so
        # late-joining subscribers (e.g., WebsiteInput / Plotter) can get the
        # persisted point list without requiring an insert/remove.
        points_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self._points_pub = self.create_publisher(
            Float32MultiArray, 'read_points_manual_path', points_qos
        )
        self._insert_sub = self.create_subscription(
            Float32MultiArray, 'insert_point_manual_path', self._on_insert, 10
        )
        self._remove_sub = self.create_subscription(
            Int32, 'remove_point_manual_path', self._on_remove, 10
        )

        self._load_from_disk()
        self._publish_points()

        self.get_logger().info(
            'Ready. Use topics ~/insert_point_manual_path and ~/remove_point_manual_path. '
            f'Storage: {self._storage_path()}'
        )

    def _storage_path(self) -> Path:
        return Path(
            self.get_parameter('storage_path').get_parameter_value().string_value
        ).expanduser()

    def _auto_save(self) -> bool:
        return self.get_parameter('auto_save').get_parameter_value().bool_value

    def _on_insert(self, msg: Float32MultiArray) -> None:
        if len(msg.data) != 4:
            self.get_logger().error(
                '~/insert_point_manual_path expects 4 floats: [index, x, y, z]'
            )
            return

        index_raw, x, y, z = msg.data
        try:
            index = int(index_raw)
        except (TypeError, ValueError):
            self.get_logger().error('~/insert_point_manual_path index must be numeric')
            return

        point = Point3(float(x), float(y), float(z))

        with self._lock:
            if index < 0 or index >= len(self._points):
                self._points.append(point)
                action = f'appended at {len(self._points) - 1}'
            else:
                self._points.insert(index, point)
                action = f'inserted at {index}'

            if self._auto_save():
                self._save_to_disk_locked()
            self._publish_points_locked()

        self.get_logger().info(
            f'Point {action}: ({point.x:.3f}, {point.y:.3f}, {point.z:.3f})'
        )

    def _on_remove(self, msg: Int32) -> None:
        index = int(msg.data)

        with self._lock:
            if index < 0 or index >= len(self._points):
                self.get_logger().warn(
                    f'Index out of range for ~/remove_point_manual_path: {index} '
                    f'(size={len(self._points)})'
                )
                return

            removed = self._points.pop(index)

            if self._auto_save():
                self._save_to_disk_locked()

            self._publish_points_locked()

        self.get_logger().info(
            f'Removed index {index}: ({removed.x:.3f}, {removed.y:.3f}, {removed.z:.3f})'
        )

    @staticmethod
    def _point_to_yaml(point: Point3) -> dict[str, float]:
        return {'x': float(point.x), 'y': float(point.y), 'z': float(point.z)}

    @staticmethod
    def _parse_yaml_point(item: Any) -> Point3:
        if isinstance(item, (list, tuple)) and len(item) == 3:
            return Point3(float(item[0]), float(item[1]), float(item[2]))
        if isinstance(item, dict) and {'x', 'y', 'z'} <= set(item.keys()):
            return Point3(float(item['x']), float(item['y']), float(item['z']))
        raise ValueError('Invalid point entry; expected {x,y,z} or [x,y,z]')

    def _load_from_disk(self) -> None:
        storage_path = self._storage_path()
        if not storage_path.exists():
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.get_logger().info('No YAML file found; starting with an empty list.')
            return

        try:
            content = storage_path.read_text(encoding='utf-8')
            loaded = yaml.safe_load(content)
        except Exception as exc:
            self.get_logger().error(f'Failed to load YAML from {storage_path}: {exc}')
            return

        if loaded is None:
            loaded_list: list[Any] = []
        elif isinstance(loaded, list):
            loaded_list = loaded
        else:
            self.get_logger().error('YAML root must be a list; ignoring file.')
            return

        parsed: list[Point3] = []
        for idx, item in enumerate(loaded_list):
            try:
                parsed.append(self._parse_yaml_point(item))
            except Exception as exc:
                self.get_logger().warn(f'Ignoring invalid point at index {idx}: {exc}')

        with self._lock:
            self._points = parsed

        self.get_logger().info(f'Loaded {len(parsed)} points from {storage_path}')

    def _save_to_disk_locked(self) -> None:
        storage_path = self._storage_path()
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = [self._point_to_yaml(p) for p in self._points]
        text = yaml.safe_dump(data, sort_keys=False)

        tmp_fd, tmp_path_str = tempfile.mkstemp(
            prefix='points_', suffix='.yaml', dir=str(storage_path.parent)
        )
        tmp_path = Path(tmp_path_str)
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                f.write(text)
            tmp_path.replace(storage_path)
        finally:
            try:
                if tmp_path.exists() and tmp_path != storage_path:
                    tmp_path.unlink()
            except Exception:
                pass

    def _publish_points(self) -> None:
        with self._lock:
            self._publish_points_locked()

    def _publish_points_locked(self) -> None:
        msg = Float32MultiArray()
        flat: list[float] = []
        for point in self._points:
            flat.extend([float(point.x), float(point.y), float(point.z)])
        msg.data = flat
        self._points_pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    """Entrypoint for `ros2 run robot_arm points_manager`."""

    rclpy.init(args=args)
    node = PointsManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
