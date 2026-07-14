"""In-memory operational state for the deterministic ReliefGrid demo scenario."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.schemas.relief import (
    Convoy,
    ConvoyStatus,
    Hazard,
    HazardType,
    OperationalState,
    ReliefRequest,
    RequestStatus,
    RequestType,
)


class StateStoreError(ValueError):
    """Raised when a requested operational-state mutation is invalid."""


def build_seed_state() -> OperationalState:
    """Return a fresh, validated Central London scenario with stable demo IDs."""

    return OperationalState(
        scenario_id="central-london-relief-demo",
        timestamp=datetime.now(timezone.utc),
        convoys=[
            Convoy(
                convoy_id="convoy-1",
                name="Westminster Evacuation Support",
                lat=51.5014,
                lon=-0.1419,
                status=ConvoyStatus.STAGING,
                capacity=80,
            ),
            Convoy(
                convoy_id="convoy-2",
                name="Trafalgar Medical Response",
                lat=51.5080,
                lon=-0.1281,
                status=ConvoyStatus.STAGING,
                capacity=50,
            ),
            Convoy(
                convoy_id="convoy-3",
                name="Waterloo Supply Distribution",
                lat=51.5034,
                lon=-0.1136,
                status=ConvoyStatus.STAGING,
                capacity=100,
            ),
            Convoy(
                convoy_id="convoy-4",
                name="Lambeth Relief Logistics",
                lat=51.4985,
                lon=-0.1172,
                status=ConvoyStatus.STAGING,
                capacity=90,
            ),
            Convoy(
                convoy_id="convoy-5",
                name="Chelsea Support Vehicle",
                lat=51.4875,
                lon=-0.1682,
                status=ConvoyStatus.STAGING,
                capacity=70,
            ),
            Convoy(
                convoy_id="convoy-6",
                name="Southwark Relief Convoy",
                lat=51.5035,
                lon=-0.0982,
                status=ConvoyStatus.STAGING,
                capacity=120,
            ),
        ],
        requests=[
            ReliefRequest(
                request_id="req-evac-elm-shelter",
                type=RequestType.EVACUATION,
                lat=51.5056,
                lon=-0.1356,
                priority=5,
                status=RequestStatus.OPEN,
                population_affected=140,
            ),
            ReliefRequest(
                request_id="req-med-sector-4",
                type=RequestType.MEDICAL,
                lat=51.5091,
                lon=-0.1216,
                priority=5,
                status=RequestStatus.OPEN,
                population_affected=95,
            ),
            ReliefRequest(
                request_id="req-supply-waterloo-reception",
                type=RequestType.SUPPLY,
                lat=51.5010,
                lon=-0.1131,
                priority=3,
                status=RequestStatus.OPEN,
                population_affected=220,
            ),
        ],
        hazards=[
            Hazard(
                hazard_id="haz-river-flood-watch",
                edge_ids=["flood-watch-embankment-1"],
                type=HazardType.FLOOD,
                severity=3,
            )
        ],
    )


class OperationalStateStore:
    """Own one mutable scenario while returning copies to all callers."""

    def __init__(self, initial_state: OperationalState | None = None) -> None:
        self._lock = RLock()
        self._state = (initial_state or build_seed_state()).model_copy(deep=True)

    def get_state(self) -> OperationalState:
        """Return an isolated, validated copy of the current operational state."""

        with self._lock:
            return self._state.model_copy(deep=True)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-compatible state payload for a WebSocket broadcast."""

        with self._lock:
            return self._state.model_dump(mode="json")

    def update_convoy_assignment(self, convoy_id: str, request_id: str) -> OperationalState:
        """Assign an available convoy to an open request and return a fresh state copy."""

        with self._lock:
            convoy = self._find_convoy(convoy_id)
            request = self._find_request(request_id)
            if convoy.status == ConvoyStatus.BLOCKED:
                raise StateStoreError(f"Blocked convoy {convoy_id!r} cannot be assigned.")
            if convoy.current_request_id and convoy.current_request_id != request_id:
                raise StateStoreError(f"Convoy {convoy_id!r} is already assigned.")
            if convoy.current_request_id is None and convoy.status != ConvoyStatus.STAGING:
                raise StateStoreError(f"Convoy {convoy_id!r} is not in staging.")
            if request.status == RequestStatus.ASSIGNED and convoy.current_request_id != request_id:
                raise StateStoreError(f"Request {request_id!r} is already assigned.")
            if request.status not in {RequestStatus.OPEN, RequestStatus.ASSIGNED}:
                raise StateStoreError(f"Request {request_id!r} is not available for assignment.")

            convoy.current_request_id = request_id
            convoy.status = (
                ConvoyStatus.EVACUATING
                if request.type == RequestType.EVACUATION
                else ConvoyStatus.EN_ROUTE
            )
            request.status = RequestStatus.ASSIGNED
            self._touch()
            return self._state.model_copy(deep=True)

    def add_hazard(self, hazard: Hazard) -> OperationalState:
        """Add a new validated hazard while keeping hazard IDs unique."""

        with self._lock:
            if any(item.hazard_id == hazard.hazard_id for item in self._state.hazards):
                raise StateStoreError(f"Hazard {hazard.hazard_id!r} already exists.")
            self._state.hazards.append(hazard.model_copy(deep=True))
            self._touch()
            return self._state.model_copy(deep=True)

    def update_request_status(self, request_id: str, status: RequestStatus) -> OperationalState:
        """Update a request lifecycle status and return an isolated state copy."""

        with self._lock:
            request = self._find_request(request_id)
            request.status = status
            self._touch()
            return self._state.model_copy(deep=True)

    def _find_convoy(self, convoy_id: str) -> Convoy:
        for convoy in self._state.convoys:
            if convoy.convoy_id == convoy_id:
                return convoy
        raise StateStoreError(f"Unknown convoy: {convoy_id!r}.")

    def _find_request(self, request_id: str) -> ReliefRequest:
        for request in self._state.requests:
            if request.request_id == request_id:
                return request
        raise StateStoreError(f"Unknown request: {request_id!r}.")

    def _touch(self) -> None:
        self._state.timestamp = datetime.now(timezone.utc)


state_store = OperationalStateStore()
