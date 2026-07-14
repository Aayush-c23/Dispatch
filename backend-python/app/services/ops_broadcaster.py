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

    async def connect(self, websocket: WebSocket, full_snapshot: dict[str, Any]) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        full_snapshot["type"] = "ops_snapshot"
        await websocket.send_json(full_snapshot)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast_snapshot(self, full_snapshot: dict[str, Any]) -> None:
        """Send a throttled state message, retaining the newest update for the UI."""
        loop = asyncio.get_running_loop()
        elapsed = loop.time() - self._last_broadcast_at
        if self._last_broadcast_at and elapsed < self._minimum_interval_seconds:
            await asyncio.sleep(self._minimum_interval_seconds - elapsed)

        full_snapshot["type"] = "ops_snapshot"
        stale_connections: list[WebSocket] = []
        for websocket in tuple(self._connections):
            try:
                await websocket.send_json(full_snapshot)
            except Exception:
                stale_connections.append(websocket)
        for websocket in stale_connections:
            self.disconnect(websocket)
        self._last_broadcast_at = loop.time()

operations_broadcaster = OperationsBroadcaster()
