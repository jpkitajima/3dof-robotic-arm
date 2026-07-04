from __future__ import annotations

from typing import Iterable, List, Tuple

from std_msgs.msg import Float32MultiArray

from .config import ArtBorders, XYZ
from .motion import MotionPlanner


class SvgPointGenerator:
    """Converts SVG paths to Cartesian points within the configured borders."""

    def generate(
        self,
        *,
        svg_path: str,
        borders: ArtBorders,
        rest_position: XYZ,
        retraction_distance: float,
        retraction_step: float,
    ) -> List[Float32MultiArray]:
        svgpathtools = self._import_svgpathtools()

        paths, _ = svgpathtools.svg2paths(svg_path)
        min_y, max_y, min_x, max_x = self._calculate_svg_bounding_box(paths)

        points: List[Float32MultiArray] = []
        last_y, last_z = rest_position[1], rest_position[2]

        for path in paths:
            new_points, last_y, last_z = self._process_svg_path(
                path=path,
                min_x=min_x,
                max_x=max_x,
                min_y=min_y,
                max_y=max_y,
                last_y=last_y,
                last_z=last_z,
                borders=borders,
                retraction_distance=retraction_distance,
                retraction_step=retraction_step,
            )
            points.extend(new_points)

        self._append_return_to_rest(
            points=points,
            rest_position=rest_position,
            last_y=last_y,
            last_z=last_z,
            drawing_x=borders.x,
            retraction_distance=retraction_distance,
            retraction_step=retraction_step,
        )

        return points

    def _import_svgpathtools(self):
        try:
            import svgpathtools  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "svgpathtools is required for SVG plotting. "
                "Install it in your ROS environment (e.g. `pip install svgpathtools`)."
            ) from exc
        return svgpathtools

    def _calculate_svg_bounding_box(self, paths) -> Tuple[float, float, float, float]:
        # svgpathtools exposes points as complex(x, y) values.
        min_x = min(
            segment.point(t / 100.0).real
            for path in paths
            for segment in path
            for t in range(0, 101)
        )
        max_x = max(
            segment.point(t / 100.0).real
            for path in paths
            for segment in path
            for t in range(0, 101)
        )
        min_y = min(
            segment.point(t / 100.0).imag
            for path in paths
            for segment in path
            for t in range(0, 101)
        )
        max_y = max(
            segment.point(t / 100.0).imag
            for path in paths
            for segment in path
            for t in range(0, 101)
        )
        return min_y, max_y, min_x, max_x

    def _scale_point(
        self,
        *,
        point,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        borders: ArtBorders,
    ) -> tuple[float, float]:
        svg_x = point.real
        svg_y = point.imag

        dx = max_x - min_x
        dy = max_y - min_y
        if dx == 0 or dy == 0:
            raise ValueError(f'Invalid SVG bounds (dx={dx}, dy={dy})')

        y_scaled = borders.y_max - (svg_x - min_x) / dx * borders.y_range
        z_scaled = borders.z_max - (svg_y - min_y) / dy * borders.z_range
        return y_scaled, z_scaled

    def _process_svg_path(
        self,
        *,
        path,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        last_y: float,
        last_z: float,
        borders: ArtBorders,
        retraction_distance: float,
        retraction_step: float,
    ) -> tuple[List[Float32MultiArray], float, float]:
        points: List[Float32MultiArray] = []

        z_range = borders.z_range
        y_range = borders.y_range

        x_down = borders.x
        x_up = borders.x - retraction_distance

        # Smooth retract at the current position.
        MotionPlanner.append_linear_motion(
            points,
            (x_down, last_y, last_z),
            (x_up, last_y, last_z),
            retraction_step,
        )

        first_point = path[0].point(0.0)
        y_scaled, z_scaled = self._scale_point(
            point=first_point,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            borders=borders,
        )

        # Smooth travel while retracted to the first point of this path.
        MotionPlanner.append_linear_motion(
            points,
            (x_up, last_y, last_z),
            (x_up, y_scaled, z_scaled),
            retraction_step,
        )

        # Smooth lower (extend) before drawing.
        MotionPlanner.append_linear_motion(
            points,
            (x_up, y_scaled, z_scaled),
            (x_down, y_scaled, z_scaled),
            retraction_step,
        )

        last_y, last_z = y_scaled, z_scaled

        for segment in path:
            segment_length = float(segment.length())
            num_steps = max(1, int(segment_length))

            for t in range(0, num_steps + 1):
                point = segment.point(t / num_steps)
                y_scaled, z_scaled = self._scale_point(
                    point=point,
                    min_x=min_x,
                    max_x=max_x,
                    min_y=min_y,
                    max_y=max_y,
                    borders=borders,
                )

                msg = Float32MultiArray()
                msg.data = [float(borders.x), float(y_scaled), float(z_scaled)]
                points.append(msg)

                last_y, last_z = y_scaled, z_scaled

        return points, last_y, last_z

    def _append_return_to_rest(
        self,
        *,
        points: List[Float32MultiArray],
        rest_position: XYZ,
        last_y: float,
        last_z: float,
        drawing_x: float,
        retraction_distance: float,
        retraction_step: float,
    ) -> None:
        rest_x, rest_y, rest_z = rest_position
        retracted_x = drawing_x - retraction_distance

        MotionPlanner.append_linear_motion(
            points,
            (drawing_x, last_y, last_z),
            (retracted_x, last_y, last_z),
            retraction_step,
        )
        MotionPlanner.append_linear_motion(
            points,
            (retracted_x, last_y, last_z),
            (retracted_x, rest_y, rest_z),
            retraction_step,
        )
        MotionPlanner.append_linear_motion(
            points,
            (retracted_x, rest_y, rest_z),
            (rest_x, rest_y, rest_z),
            retraction_step,
        )
