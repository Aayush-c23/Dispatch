"""Dynamic spatial obstruction overlay for live routing."""

from typing import Any
import threading

class ObstructionOverlay:
    def __init__(self) -> None:
        # Maps edge_id -> list of hazard dictionaries
        # Using a lock for thread-safety in case of concurrent API requests
        self._lock = threading.Lock()
        self._edge_hazards: dict[str, list[dict[str, Any]]] = {}

    def apply_obstruction(self, edge_ids: list[str], hazard_id: str, status: str = "BLOCKED", multiplier: float = 1.0) -> None:
        """Apply a hazard to a set of edges."""
        with self._lock:
            for edge_id in edge_ids:
                if edge_id not in self._edge_hazards:
                    self._edge_hazards[edge_id] = []
                # Remove if it already exists to avoid duplicates
                self._edge_hazards[edge_id] = [h for h in self._edge_hazards[edge_id] if h["hazard_id"] != hazard_id]
                self._edge_hazards[edge_id].append({
                    "hazard_id": hazard_id,
                    "status": status.upper(),
                    "hazard_multiplier": multiplier
                })

    def clear_obstruction(self, hazard_id: str) -> None:
        """Clear a specific hazard ID from all edges."""
        with self._lock:
            for edge_id in list(self._edge_hazards.keys()):
                self._edge_hazards[edge_id] = [h for h in self._edge_hazards[edge_id] if h["hazard_id"] != hazard_id]
                if not self._edge_hazards[edge_id]:
                    del self._edge_hazards[edge_id]

    def clear_all(self) -> None:
        """Clear all obstructions."""
        with self._lock:
            self._edge_hazards.clear()

    def get_edge_overlay(self, edge_id: str) -> dict[str, Any] | None:
        """Return the aggregated overlay data for an edge, or None if unaffected."""
        with self._lock:
            hazards = self._edge_hazards.get(edge_id)
            if not hazards:
                return None
            
            is_blocked = any(h["status"] in {"BLOCKED", "CLOSED", "IMPASSABLE"} for h in hazards)
            max_multiplier = max((h["hazard_multiplier"] for h in hazards), default=1.0)
            
            return {
                "blocked": is_blocked,
                "hazard_multiplier": max_multiplier,
            }

overlay = ObstructionOverlay()
