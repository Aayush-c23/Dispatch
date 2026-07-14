"""Focused contract tests for the backend routing-engine adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.schemas.relief import (
    ActionType,
    Convoy,
    ConvoyStatus,
    ObjectiveAction,
    OperationalState,
    ReliefRequest,
    RequestStatus,
    RequestType,
)
from app.services.engine_client import EngineClientError, compute_routes_for_assignments


def fake_route(*_coordinates: float) -> SimpleNamespace:
    return SimpleNamespace(
        origin_node=1,
        destination_node=2,
        node_ids=[1, 2],
        edge_ids=["edge-1"],
        geometry=[{"lat": 51.5014, "lon": -0.1419}, {"lat": 51.5079, "lon": -0.1280}],
        distance_meters=1_170.3,
        estimated_seconds=130.9,
    )


class EngineClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = OperationalState(
            scenario_id="central-london-demo",
            timestamp=datetime.now(timezone.utc),
            convoys=[Convoy(convoy_id="convoy-1", name="Westminster Support", lat=51.5014, lon=-0.1419, status=ConvoyStatus.STAGING, capacity=40)],
            requests=[ReliefRequest(request_id="req-med-sector-4", type=RequestType.MEDICAL, lat=51.5079, lon=-0.1280, priority=5, status=RequestStatus.OPEN, population_affected=120)],
        )
        self.assignment = ObjectiveAction(target_convoy_id="convoy-1", action_type=ActionType.ASSIGN, target_request_id="req-med-sector-4", priority_score=5, rationale="Highest-priority reachable request.")

    def test_returns_frontend_ready_route_for_assignment(self) -> None:
        routes = compute_routes_for_assignments(self.state, [self.assignment], route_provider=fake_route)

        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].convoy_id, "convoy-1")
        self.assertEqual(routes[0].request_id, "req-med-sector-4")
        self.assertEqual(routes[0].geometry[0].lat, 51.5014)

    def test_rejects_assignment_for_unknown_convoy(self) -> None:
        invalid = self.assignment.model_copy(update={"target_convoy_id": "missing-convoy"})
        with self.assertRaises(EngineClientError):
            compute_routes_for_assignments(self.state, [invalid], route_provider=fake_route)
