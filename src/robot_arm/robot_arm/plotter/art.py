from __future__ import annotations

from random import uniform
from typing import List

from std_msgs.msg import Float32MultiArray

from .config import ArtBorders


class ArtPointGenerator:
    """Random-walk point generator constrained to a Y/Z bounding box."""

    def generate(
        self,
        *,
        borders: ArtBorders,
        distance: float,
        num_points: int,
    ) -> List[Float32MultiArray]:
        points: List[Float32MultiArray] = []

        current_y = uniform(borders.y_min, borders.y_max)
        current_z = uniform(borders.z_min, borders.z_max)

        for _ in range(max(0, int(num_points))):
            msg = Float32MultiArray()
            msg.data = [float(borders.x), float(current_y), float(current_z)]
            points.append(msg)
            current_y, current_z = self._next_point(
                borders=borders,
                current_y=current_y,
                current_z=current_z,
                distance=distance,
            )

        return points

    def _next_point(
        self,
        *,
        borders: ArtBorders,
        current_y: float,
        current_z: float,
        distance: float,
    ) -> tuple[float, float]:
        while True:
            candidate_y = current_y + uniform(-distance, distance)
            candidate_z = current_z + uniform(-distance, distance)
            if borders.contains(candidate_y, candidate_z):
                return candidate_y, candidate_z
