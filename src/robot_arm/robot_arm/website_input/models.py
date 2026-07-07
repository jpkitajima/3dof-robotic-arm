from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControllerState:
    lb: bool
    rb: bool
    a: bool
    b: bool
    x: bool
    y: bool
    switch_on: bool
    switch_off: bool
