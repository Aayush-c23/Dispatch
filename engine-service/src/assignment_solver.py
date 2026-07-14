"""Deterministically assign available convoys to the most urgent requests."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .router import RouteResult

RouteProvider = Callable[[float, float, float, float], "RouteResult"]


@dataclass(frozen=True)
class ConvoyAssignment:
    """A routing-aware assignment that can be emitted as an objective action."""

    convoy_id: str
    request_id: str
    priority_score: int
    rationale: str
    route: "RouteResult"

    def to_action(self) -> dict[str, Any]:
        """Return the stable payload used by the backend objective-command contract."""

        return {
            "target_convoy_id": self.convoy_id,
            "action_type": "ASSIGN",
            "target_request_id": self.request_id,
            "priority_score": self.priority_score,
            "rationale": self.rationale,
        }

    def to_dict(self) -> dict[str, Any]:
        """Return the action plus route data needed by a later backend consumer."""

        return {**self.to_action(), "route": self.route.to_dict()}


def _value(record: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    """Read either a dictionary or a future Pydantic model without coupling tiers."""

    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_available(convoy: Mapping[str, Any] | Any) -> bool:
    """Only unassigned staging convoys may receive a new deterministic assignment."""

    status = str(_value(convoy, "status", "")).upper()
    return (
        status == "STAGING"
        and not _value(convoy, "current_request_id")
        and _as_float(_value(convoy, "capacity")) > 0
    )


def _is_open(request: Mapping[str, Any] | Any) -> bool:
    return str(_value(request, "status", "")).upper() == "OPEN"


def _required_capacity(request: Mapping[str, Any] | Any) -> float:
    """Support an optional demand field while keeping the Phase 1 state schema small."""

    for key in ("required_capacity", "capacity_required", "demand"):
        value = _value(request, key)
        if value is not None:
            return max(_as_float(value), 0.0)
    return 0.0


def _request_sort_key(request: Mapping[str, Any] | Any) -> tuple[float, float, str]:
    return (
        -_as_float(_value(request, "priority")),
        -_as_float(_value(request, "population_affected")),
        str(_value(request, "request_id", "")),
    )


def _rationale(request: Mapping[str, Any] | Any, route: "RouteResult") -> str:
    priority = int(_as_float(_value(request, "priority")))
    population = int(_as_float(_value(request, "population_affected")))
    return (
        f"Priority {priority} request affecting {population} people; "
        f"fastest feasible route is {route.estimated_seconds:.0f} seconds."
    )


def solve_assignments(
    convoys: Sequence[Mapping[str, Any] | Any],
    requests: Sequence[Mapping[str, Any] | Any],
    route_provider: RouteProvider | None = None,
) -> list[ConvoyAssignment]:
    """Assign one available convoy to each highest-ranked reachable open request.

    Requests are considered by priority, affected population, then ID.  For each
    request, candidates must be staging, unassigned, have positive/adequate
    capacity, and have a reachable route. The shortest ETA wins; spare capacity
    and convoy ID make ties deterministic.
    """

    if route_provider is None:
        # Delay the engine import so callers can inject a lightweight provider in
        # tests and so this deterministic policy stays independent of engine setup.
        from .router import route_between_points

        route_provider = route_between_points

    available = [convoy for convoy in convoys if _is_available(convoy)]
    assignments: list[ConvoyAssignment] = []

    for request in sorted((item for item in requests if _is_open(item)), key=_request_sort_key):
        request_id = str(_value(request, "request_id", ""))
        if not request_id:
            continue

        required_capacity = _required_capacity(request)
        candidates: list[tuple[float, float, str, Mapping[str, Any] | Any, "RouteResult"]] = []
        for convoy in available:
            capacity = _as_float(_value(convoy, "capacity"))
            if capacity < required_capacity:
                continue
            try:
                route = route_provider(
                    _as_float(_value(convoy, "lat")),
                    _as_float(_value(convoy, "lon")),
                    _as_float(_value(request, "lat")),
                    _as_float(_value(request, "lon")),
                )
            except Exception:  # A routing failure makes this convoy/request pair infeasible.
                # A disconnected or invalid point is not an operationally feasible pair.
                continue
            candidates.append(
                (
                    route.estimated_seconds,
                    -(capacity - required_capacity),
                    str(_value(convoy, "convoy_id", "")),
                    convoy,
                    route,
                )
            )

        if not candidates:
            continue

        _, _, convoy_id, chosen_convoy, route = min(candidates, key=lambda candidate: candidate[:3])
        assignments.append(
            ConvoyAssignment(
                convoy_id=convoy_id,
                request_id=request_id,
                priority_score=int(_as_float(_value(request, "priority"))),
                rationale=_rationale(request, route),
                route=route,
            )
        )
        available.remove(chosen_convoy)

    return assignments
