from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

try:
    from aiohttp import WSMsgType, web
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        'aiohttp is required for WebsiteInput. Install with `pip install aiohttp` '
        'or install the OS package `python3-aiohttp`.'
    ) from exc


class WebsiteInputWebServer:
    """aiohttp app hosting the web UI and websocket endpoint."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        static_dir: Path,
        logger: Any,
        on_state_payload: Callable[[dict[str, Any]], Any] | Callable[[dict[str, Any]], Awaitable[Any]],
        on_ws_payload: (
            Callable[[dict[str, Any]], Any] | Callable[[dict[str, Any]], Awaitable[Any]] | None
        ) = None,
        on_client_connected: Callable[[str | None], None],
        on_client_disconnected: Callable[[str | None], None],
        get_last_cartesian_xyz: Callable[[], tuple[float, float, float] | None],
        get_last_path_programmer_points: Callable[[], list[dict[str, float]] | None],
    ) -> None:
        self._host = host
        self._port = port
        self._static_dir = static_dir
        self._logger = logger

        self._on_state_payload = on_state_payload
        self._on_ws_payload = on_ws_payload
        self._on_client_connected = on_client_connected
        self._on_client_disconnected = on_client_disconnected
        self._get_last_cartesian_xyz = get_last_cartesian_xyz
        self._get_last_path_programmer_points = get_last_path_programmer_points

        self._ws_clients: set[web.WebSocketResponse] = set()

        self._app = web.Application()
        self._app.router.add_get('/input', self._handle_input_page)
        self._app.router.add_get('/ws', self._handle_ws)
        if self._static_dir.is_dir():
            self._app.router.add_static('/static/', path=str(self._static_dir), show_index=False)
        else:
            self._log('error', f'Static resources directory not found: {self._static_dir}')

        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    async def start(self) -> None:
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host=self._host, port=self._port)
        await self._site.start()
        self._log('info', 'aiohttp server started')

    async def stop(self) -> None:
        try:
            if self._site is not None:
                await self._site.stop()
            if self._runner is not None:
                await self._runner.cleanup()
        finally:
            self._site = None
            self._runner = None
            self._log('info', 'aiohttp server stopped')

    def _log(self, level: str, msg: str) -> None:
        fn = getattr(self._logger, level, None)
        if fn is None and level == 'warning':
            fn = getattr(self._logger, 'warn', None)
        if fn is None and level == 'warn':
            fn = getattr(self._logger, 'warning', None)
        if fn is None:
            fn = getattr(self._logger, 'info', None)
        if fn is not None:
            fn(msg)

    async def _handle_input_page(self, _request: web.Request) -> web.Response:
        index_path = self._static_dir / 'index.html'
        if not index_path.is_file():
            msg = f'Website resources not found: {index_path}'
            self._log('error', msg)
            return web.Response(text=msg, status=500, content_type='text/plain')
        return web.FileResponse(path=index_path)

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=10.0)
        await ws.prepare(request)

        peer = request.remote
        self._ws_clients.add(ws)
        self._on_client_connected(peer)

        last_cart = self._get_last_cartesian_xyz()
        if last_cart is not None:
            x, y, z = last_cart
            await self._ws_send_json(
                ws,
                {
                    'type': 'cartesian_xyz_read',
                    'x': x,
                    'y': y,
                    'z': z,
                },
            )

        last_points = self._get_last_path_programmer_points()
        if last_points is not None:
            await self._ws_send_json(
                ws,
                {
                    'type': 'path_programmer_points',
                    'points': last_points,
                },
            )

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._on_ws_text(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    self._log('warning', f'WebSocket error: {ws.exception()}')
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as exc:  # noqa: BLE001
            self._log('error', f'WebSocket handler exception: {exc}')
        finally:
            self._ws_clients.discard(ws)
            self._on_client_disconnected(peer)

        return ws

    async def _on_ws_text(self, text: str) -> None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            self._log('warning', 'Received invalid JSON on websocket')
            return

        if not isinstance(payload, dict):
            self._log('warning', 'Received non-object JSON on websocket')
            return

        msg_type = payload.get('type')
        if msg_type == 'state':
            maybe_awaitable = self._on_state_payload(payload)
        elif self._on_ws_payload is not None:
            maybe_awaitable = self._on_ws_payload(payload)
        else:
            self._log('debug', f'Ignoring websocket message type={msg_type!r}')
            return

        if asyncio.iscoroutine(maybe_awaitable):
            await maybe_awaitable

    async def _ws_send_json(self, ws: web.WebSocketResponse, payload: dict[str, Any]) -> None:
        try:
            await ws.send_str(json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            self._log('debug', f'WebSocket send failed: {exc}')

    async def broadcast_json(self, payload: dict[str, Any]) -> None:
        if not self._ws_clients:
            return
        for ws in list(self._ws_clients):
            if ws.closed:
                self._ws_clients.discard(ws)
                continue
            await self._ws_send_json(ws, payload)
