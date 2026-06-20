from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import ControllerState, Stick
from .utils import _as_bool, _as_float, _clamp


def parse_controller_state(payload: Mapping[str, Any]) -> ControllerState:
    buttons = payload.get('buttons') or {}
    sticks = payload.get('sticks') or {}
    left = sticks.get('left') or {}
    right = sticks.get('right') or {}

    lt = _clamp(_as_float(payload.get('lt')), -1.0, 1.0)
    rt = _clamp(_as_float(payload.get('rt')), -1.0, 1.0)

    def b(name: str) -> bool:
        return _as_bool(buttons.get(name, False))

    left_stick = Stick(
        x=_clamp(_as_float(left.get('x')), -1.0, 1.0),
        y=_clamp(_as_float(left.get('y')), -1.0, 1.0),
    )
    right_stick = Stick(
        x=_clamp(_as_float(right.get('x')), -1.0, 1.0),
        y=_clamp(_as_float(right.get('y')), -1.0, 1.0),
    )

    return ControllerState(
        lt=lt,
        rt=rt,
        lb=b('lb'),
        rb=b('rb'),
        a=b('a'),
        b=b('b'),
        x=b('x'),
        y=b('y'),
        switch_on=b('switch_on'),
        switch_off=b('switch_off'),
        dpad_up=b('dpad_up'),
        dpad_down=b('dpad_down'),
        dpad_left=b('dpad_left'),
        dpad_right=b('dpad_right'),
        left_stick=left_stick,
        right_stick=right_stick,
    )


class ControllerStateDispatcher:
    """Dispatches controller state to handler methods.

    The handler object is expected to implement methods like:
    - on_lt(value: float)
    - on_left_stick(x: float, y: float)
    - on_lb(pressed: bool)

    This stays duck-typed so the ROS2 Node can be the handler.
    """

    def __init__(self, handler: Any, *, float_epsilon: float = 0.02) -> None:
        self._handler = handler
        self._eps = float_epsilon
        self._last_state: ControllerState | None = None

    def dispatch(self, state: ControllerState) -> None:
        prev = self._last_state
        self._last_state = state

        def changed_f(a: float, b: float) -> bool:
            return abs(a - b) > self._eps

        if prev is None or changed_f(prev.lt, state.lt):
            self._handler.on_lt(state.lt)
        if prev is None or changed_f(prev.rt, state.rt):
            self._handler.on_rt(state.rt)

        if prev is None or changed_f(prev.left_stick.x, state.left_stick.x) or changed_f(
            prev.left_stick.y, state.left_stick.y
        ):
            self._handler.on_left_stick(state.left_stick.x, state.left_stick.y)

        if prev is None or changed_f(prev.right_stick.x, state.right_stick.x) or changed_f(
            prev.right_stick.y, state.right_stick.y
        ):
            self._handler.on_right_stick(state.right_stick.x, state.right_stick.y)

        def edge(name: str, old: bool, new: bool) -> None:
            if old == new:
                return
            handler = getattr(self._handler, f'on_{name}', None)
            if handler is not None:
                handler(new)

        if prev is None:
            edge('lb', False, state.lb)
            edge('rb', False, state.rb)
            edge('a', False, state.a)
            edge('b', False, state.b)
            edge('x', False, state.x)
            edge('y', False, state.y)
            edge('switch_on', False, state.switch_on)
            edge('switch_off', False, state.switch_off)
            edge('dpad_up', False, state.dpad_up)
            edge('dpad_down', False, state.dpad_down)
            edge('dpad_left', False, state.dpad_left)
            edge('dpad_right', False, state.dpad_right)
        else:
            edge('lb', prev.lb, state.lb)
            edge('rb', prev.rb, state.rb)
            edge('a', prev.a, state.a)
            edge('b', prev.b, state.b)
            edge('x', prev.x, state.x)
            edge('y', prev.y, state.y)
            edge('switch_on', prev.switch_on, state.switch_on)
            edge('switch_off', prev.switch_off, state.switch_off)
            edge('dpad_up', prev.dpad_up, state.dpad_up)
            edge('dpad_down', prev.dpad_down, state.dpad_down)
            edge('dpad_left', prev.dpad_left, state.dpad_left)
            edge('dpad_right', prev.dpad_right, state.dpad_right)
