from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

XYZ = Tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ArtBorders:
    x: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float

    @property
    def y_range(self) -> float:
        return self.y_max - self.y_min

    @property
    def z_range(self) -> float:
        return self.z_max - self.z_min

    def contains(self, y: float, z: float) -> bool:
        return self.y_min <= y <= self.y_max and self.z_min <= z <= self.z_max


@dataclass(frozen=True, slots=True)
class PlotterParams:
    retraction_distance: float = 0.02
    retraction_step: float = 0.001

    circle_center: XYZ = (0.2, 0.0, 0.02)
    radius: float = 0.025
    delay: float = 0.01
    num_points: int = 200

    switch_on_position: XYZ = (0.2, 0.0, 0.01)
    switch_off_position: XYZ = (0.2, 0.0, 0.05)

    art_borders: ArtBorders = ArtBorders(
        x=0.2,
        y_min=-0.015,
        y_max=0.015,
        z_min=0,
        z_max=0.03,
    )
    art_distance: float = 0.01
    art_num_points: int = 1000
    art_delay: float = 0.2

    rest_position: XYZ = (0.18, 0.0, 0.0)

    svg_resource_name: str = "cube.svg"
