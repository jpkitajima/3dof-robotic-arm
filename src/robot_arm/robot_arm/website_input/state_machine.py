from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import ControllerState
from .utils import _as_bool


def parse_controller_state(payload: Mapping[str, Any]) -> ControllerState:
    buttons = payload.get('buttons') or {}

    def b(name: str) -> bool:
        return _as_bool(buttons.get(name, False))

    return ControllerState(
        lb=b('lb'),
        rb=b('rb'),
        a=b('a'),
        b=b('b'),
        x=b('x'),
        y=b('y'),
        switch_on=b('switch_on'),
        switch_off=b('switch_off'),
    )


class ControllerStateDispatcher:
    """Dispatches controller state to handler methods.

    The handler object is expected to implement methods like:
    - on_lt(value: float)
    - on_left_stick(x: float, y: float)
    - on_lb(pressed: bool)

    This stays duck-typed so the ROS2 Node can be the handler.
    """

    def __init__(self, handler: Any) -> None:
        self._handler = handler
        self._last_state: ControllerState | None = None

    def dispatch(self, state: ControllerState) -> None:
        prev = self._last_state
        self._last_state = state

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
        else:
            edge('lb', prev.lb, state.lb)
            edge('rb', prev.rb, state.rb)
            edge('a', prev.a, state.a)
            edge('b', prev.b, state.b)
            edge('x', prev.x, state.x)
            edge('y', prev.y, state.y)
            edge('switch_on', prev.switch_on, state.switch_on)
            edge('switch_off', prev.switch_off, state.switch_off)
