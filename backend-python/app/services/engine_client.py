"""Adapter between FastAPI orchestration models and the routing-engine tier."""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from app.schemas.relief import ActionType, ObjectiveAction, OperationalState, RouteResponse


class RouteResultLike(Protocol):
    """The minimal routing-engine result contract consumed by this adapter."""

    origin_node: int
    destination_node: int
    node_ids: list[int]
    edge_ids: list[str]
    geometry: list[dict[str, float]]
    distance_meters: float
    estimated_seconds: float


RouteProvider = Callable[[float, float, float, float], RouteResultLike]
AssignmentInput = ObjectiveAction | Mapping[str, Any]
ENGINE_SERVICE_PATH = Path(__file__).resolve().parents[3] / "engine-service"


class EngineClientError(ValueError):
    """Raised when an orchestration request cannot be converted into a route."""


def _assignment_value(assignment: AssignmentInput, field: str, default: Any = None) -> Any:
    if isinstance(assignment, Mapping):
        return assignment.get(field, default)
    return getattr(assignment, field, default)


def _default_route_provider() -> RouteProvider:
    """Load the engine lazily so the backend remains independently importable."""

    engine_path = str(ENGINE_SERVICE_PATH)
    if engine_path not in sys.path:
        sys.path.insert(0, engine_path)

    from src.router import route_between_points

    return route_between_points


def _route_payload(
    convoy_id: str,
    request_id: str,
    route: RouteResultLike,
) -> RouteResponse:
    """Convert the engine's dataclass payload into the API's validated contract."""

    return RouteResponse(
        convoy_id=convoy_id,
        request_id=request_id,
        origin_node=route.origin_node,
        destination_node=route.destination_node,
        node_ids=route.node_ids,
        edge_ids=route.edge_ids,
        geometry=route.geometry,
        distance_meters=route.distance_meters,
        estimated_seconds=route.estimated_seconds,
    )


def compute_routes_for_assignments(
    state: OperationalState,
    assignments: Sequence[AssignmentInput],
    route_provider: RouteProvider | None = None,
) -> list[RouteResponse]:
    """Compute frontend-ready routes for explicit convoy-to-request assignments.

    Only ``ASSIGN`` and ``REROUTE`` actions require a route. ``HOLD`` actions
    deliberately produce no route. Every referenced convoy and request must be
    present in the supplied state, preventing a route from being rendered for
    stale or invented operational entities.
    """

    convoy_by_id = {convoy.convoy_id: convoy for convoy in state.convoys}
    request_by_id = {request.request_id: request for request in state.requests}
    provider = route_provider or _default_route_provider()
    routes: list[RouteResponse] = []

    for assignment in assignments:
        action_type = _assignment_value(assignment, "action_type")
        action_name = getattr(action_type, "value", action_type)
        if action_name == ActionType.HOLD.value:
            continue
        if action_name not in {ActionType.ASSIGN.value, ActionType.REROUTE.value}:
            raise EngineClientError(f"Unsupported routing action: {action_name!r}.")

        convoy_id = _assignment_value(assignment, "target_convoy_id")
        request_id = _assignment_value(assignment, "target_request_id")
        if not convoy_id or not request_id:
            raise EngineClientError("Routing actions require target_convoy_id and target_request_id.")

        convoy = convoy_by_id.get(str(convoy_id))
        request = request_by_id.get(str(request_id))
        if convoy is None:
            raise EngineClientError(f"Unknown convoy in assignment: {convoy_id!r}.")
        if request is None:
            raise EngineClientError(f"Unknown request in assignment: {request_id!r}.")

        try:
            route = provider(convoy.lat, convoy.lon, request.lat, request.lon)
        except Exception as exc:
            raise EngineClientError(
                f"Unable to route convoy {convoy_id!r} to request {request_id!r}."
            ) from exc
        routes.append(_route_payload(str(convoy_id), str(request_id), route))

    return routes
