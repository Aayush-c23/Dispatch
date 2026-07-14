"""Live transit simulation for convoys on active routes."""

import asyncio
import time
from typing import Any

from app.schemas.relief import ConvoyStatus
from app.services.state_store import OperationalStateStore, state_store
from app.services.ops_broadcaster import operations_broadcaster


class TransitSimulator:
    """A background task that advances convoys along their assigned route geometry."""

    def __init__(
        self,
        store: OperationalStateStore = state_store,
        broadcaster=operations_broadcaster,
        tick_interval_seconds: float = 1.0,
        transit_duration_seconds: float = 10.0,
    ) -> None:
        self._store = store
        self._broadcaster = broadcaster
        self._tick_interval = 0.1
        self._transit_duration = 15.0
        self._task: asyncio.Task[None] | None = None
        self._start_time: float = 0.0

    def start(self) -> None:
        """Start the simulation loop if not already running."""
        if self._task is not None and not self._task.done():
            return
        self._start_time = time.time()
        self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        try:
            while True:
                now = time.time()
                elapsed = now - self._start_time
                progress = min(elapsed / self._transit_duration, 1.0)
                
                snapshot = self._store.snapshot()
                routes = snapshot.get("routes", [])
                
                convoys_arrived = True
                for route in routes:
                    convoy_id = route.get("convoy_id")
                    geometry = route.get("geometry", [])
                    is_primary = route.get("is_primary", True)
                    if not convoy_id or not geometry or not is_primary:
                        continue
                        
                    pos = self._interpolate_position(geometry, progress)
                    if not pos:
                        continue
                        
                    status = ConvoyStatus.ARRIVED if progress >= 1.0 else ConvoyStatus.EN_ROUTE
                    self._store.update_convoy_status_and_location(convoy_id, pos["lat"], pos["lon"], status)
                    
                    if progress < 1.0:
                        convoys_arrived = False

                # Broadcast the updated state
                await self._broadcaster.broadcast_snapshot(self._store.snapshot())
                
                if convoys_arrived:
                    break
                    
                await asyncio.sleep(self._tick_interval)
        except Exception as e:
            print(f"Simulator error: {e}")

    @staticmethod
    def _interpolate_position(geometry: list[dict[str, float] | list[float]], progress: float) -> dict[str, float] | None:
        """Interpolate lat/lon based on fractional progress (0.0 to 1.0) through the geometry."""
        if not geometry:
            return None
        
        def _get_lat_lon(point: Any) -> dict[str, float] | None:
            if isinstance(point, list) and len(point) >= 2:
                # Assuming [lon, lat] from frontend route logic if array
                return {"lat": point[1], "lon": point[0]}
            if isinstance(point, dict) and "lat" in point and "lon" in point:
                return {"lat": point["lat"], "lon": point["lon"]}
            return None

        if progress <= 0:
            return _get_lat_lon(geometry[0])
        if progress >= 1:
            return _get_lat_lon(geometry[-1])

        total_points = len(geometry)
        target_index = progress * (total_points - 1)
        index = int(target_index)
        fraction = target_index - index

        p1 = _get_lat_lon(geometry[index])
        p2 = _get_lat_lon(geometry[index + 1])

        if not p1 or not p2:
            return None

        return {
            "lat": p1["lat"] + (p2["lat"] - p1["lat"]) * fraction,
            "lon": p1["lon"] + (p2["lon"] - p1["lon"]) * fraction,
        }


transit_simulator = TransitSimulator()
