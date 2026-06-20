from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stick:
    x: float
    y: float


@dataclass(frozen=True)
class ControllerState:
    lt: float
    rt: float
    lb: bool
    rb: bool
    a: bool
    b: bool
    x: bool
    y: bool
    switch_on: bool
    switch_off: bool
    dpad_up: bool
    dpad_down: bool
    dpad_left: bool
    dpad_right: bool
    left_stick: Stick
    right_stick: Stick
