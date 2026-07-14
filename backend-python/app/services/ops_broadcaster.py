"""WebSocket fan-out for live operational state snapshots."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from fastapi import WebSocket


class OperationsBroadcaster:
    """Broadcast JSON-ready operations snapshots to connected dashboard clients."""

    def __init__(self, minimum_interval_seconds: float = 0.1) -> None:
        self._connections: set[WebSocket] = set()
        self._minimum_interval_seconds = minimum_interval_seconds
        self._last_broadcast_at = 0.0

    async def connect(self, websocket: WebSocket, initial_state: Mapping[str, Any]) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        await websocket.send_json(self.snapshot_message(initial_state))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast_snapshot(
        self,
        state: Mapping[str, Any],
        routes: list[Mapping[str, Any]] | None = None,
        briefing: Mapping[str, Any] | None = None,
        reasoning_log: list[Mapping[str, Any]] | None = None,
    ) -> None:
        """Send a throttled state message, retaining the newest update for the UI."""

        loop = asyncio.get_running_loop()
        elapsed = loop.time() - self._last_broadcast_at
        if self._last_broadcast_at and elapsed < self._minimum_interval_seconds:
            await asyncio.sleep(self._minimum_interval_seconds - elapsed)

        message = self.snapshot_message(state, routes, briefing, reasoning_log)
        stale_connections: list[WebSocket] = []
        for websocket in tuple(self._connections):
            try:
                await websocket.send_json(message)
            except Exception:
                stale_connections.append(websocket)
        for websocket in stale_connections:
            self.disconnect(websocket)
        self._last_broadcast_at = loop.time()

    @staticmethod
    def snapshot_message(
        state: Mapping[str, Any],
        routes: list[Mapping[str, Any]] | None = None,
        briefing: Mapping[str, Any] | None = None,
        reasoning_log: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        message = {
            "type": "ops_snapshot",
            "state": dict(state),
            "routes": list(routes or []),
        }
        if briefing is not None:
            message["briefing"] = dict(briefing)
        if reasoning_log is not None:
            message["reasoning_log"] = list(reasoning_log)
        return message


operations_broadcaster = OperationsBroadcaster()
