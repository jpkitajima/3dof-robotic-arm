from __future__ import annotations

from math import ceil
from typing import List

from std_msgs.msg import Float32MultiArray

from .config import XYZ


class MotionPlanner:
    """Small helper for generating linear Cartesian motions."""

    @staticmethod
    def generate_line_points(
        start_xyz: XYZ,
        end_xyz: XYZ,
        num_points_in_between: int,
    ) -> List[Float32MultiArray]:
        """Generate linearly interpolated points including endpoints.

        If ``num_points_in_between`` is N, the returned list contains N+2 points:
        start point, N interior points, and end point.
        """
        n = max(0, int(num_points_in_between))
        denom = n + 1

        points: List[Float32MultiArray] = []
        for i in range(denom + 1):
            t = i / denom if denom != 0 else 0.0
            x = start_xyz[0] + (end_xyz[0] - start_xyz[0]) * t
            y = start_xyz[1] + (end_xyz[1] - start_xyz[1]) * t
            z = start_xyz[2] + (end_xyz[2] - start_xyz[2]) * t
            msg = Float32MultiArray()
            msg.data = [float(x), float(y), float(z)]
            points.append(msg)
        return points

    @staticmethod
    def append_linear_motion(
        points: List[Float32MultiArray],
        start_xyz: XYZ,
        end_xyz: XYZ,
        step: float,
    ) -> None:
        """Append linearly interpolated points from start to end (inclusive).

        Args:
            points: List to append to.
            start_xyz: (x, y, z) starting pose.
            end_xyz: (x, y, z) target pose.
            step: Maximum distance between consecutive points.
        """
        dx = end_xyz[0] - start_xyz[0]
        dy = end_xyz[1] - start_xyz[1]
        dz = end_xyz[2] - start_xyz[2]
        distance = (dx * dx + dy * dy + dz * dz) ** 0.5
        if distance <= 0.0:
            msg = Float32MultiArray()
            msg.data = [float(start_xyz[0]), float(start_xyz[1]), float(start_xyz[2])]
            points.append(msg)
            return

        step = max(float(step), 1e-6)
        num_steps = max(1, int(ceil(distance / step)))
        for i in range(num_steps + 1):
            t = i / num_steps
            x = start_xyz[0] + dx * t
            y = start_xyz[1] + dy * t
            z = start_xyz[2] + dz * t
            msg = Float32MultiArray()
            msg.data = [float(x), float(y), float(z)]
            points.append(msg)
