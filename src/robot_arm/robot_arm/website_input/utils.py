from __future__ import annotations

from pathlib import Path
from typing import Any

_PACKAGE_NAME = 'robot_arm'
_RESOURCES_SUBDIR = Path('resource') / 'website_input'


def _resolve_resources_dir() -> Path:
    """Return the directory containing website_input static assets.

    Prefers the installed ROS2 package share directory, with a fallback to the
    source tree for convenience when running directly from the workspace.
    """

    try:
        from ament_index_python.packages import get_package_share_directory  # type: ignore

        share_dir = Path(get_package_share_directory(_PACKAGE_NAME))
        candidate = share_dir / _RESOURCES_SUBDIR
        if candidate.is_dir():
            return candidate
    except Exception:  # noqa: BLE001
        pass

    # Workspace fallback (preferred): .../robot_arm/website_input/resources
    in_pkg = Path(__file__).resolve().parent / 'resources'
    if in_pkg.is_dir():
        return in_pkg

    # Legacy workspace fallback: ros2/src/robot_arm/resource/website_input
    package_root = Path(__file__).resolve().parents[2]
    return package_root / _RESOURCES_SUBDIR


def _as_bool(value: Any) -> bool:
    return bool(value)


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return 0.0


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
