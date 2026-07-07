from __future__ import annotations

from math import cos, pi, sin
from typing import List

from std_msgs.msg import Float32MultiArray

from .config import XYZ


class CirclePointGenerator:
    """Generates Cartesian points that lie on a circle in the YZ plane."""

    def generate(self, center: XYZ, radius: float, num_points: int) -> List[Float32MultiArray]:
        points: List[Float32MultiArray] = []
        n = max(1, int(num_points))
        for i in range(n):
            angle = 2 * pi * i / n
            x = center[0]
            y = center[1] + radius * cos(angle)
            z = center[2] + radius * sin(angle)
            msg = Float32MultiArray()
            msg.data = [float(x), float(y), float(z)]
            points.append(msg)
        return points
