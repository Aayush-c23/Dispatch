"""Contract tests for the deterministic POST /plan endpoint."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    from app.main import app
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False
else:
    FASTAPI_AVAILABLE = True


def fake_assignment_solver(_convoys: list[dict[str, object]], _requests: list[dict[str, object]]) -> list[SimpleNamespace]:
    route = SimpleNamespace(
        origin_node=100,
        destination_node=200,
        node_ids=[100, 150, 200],
        edge_ids=["100-150", "150-200"],
        geometry=[
            {"lat": 51.5014, "lon": -0.1419},
            {"lat": 51.5056, "lon": -0.1356},
        ],
        distance_meters=900.0,
        estimated_seconds=180.0,
    )
    return [
        SimpleNamespace(
            convoy_id="convoy-1",
            request_id="req-evac-elm-shelter",
            route=route,
            to_action=lambda: {
                "target_convoy_id": "convoy-1",
                "action_type": "ASSIGN",
                "target_request_id": "req-evac-elm-shelter",
                "priority_score": 5,
                "rationale": "Highest-priority reachable request.",
            },
        )
    ]


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed in this environment.")
class PlanningEndpointTests(unittest.TestCase):
    def test_plan_returns_actions_routes_briefing_and_state(self) -> None:
        with patch("app.services.planner.planning_service._assignment_solver", fake_assignment_solver):
            response = TestClient(app).post("/plan", json={"objective": "Prioritize urgent evacuation."})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["command"]["interpreted_actions"][0]["action_type"], "ASSIGN")
        self.assertEqual(payload["routes"][0]["convoy_id"], "convoy-1")
        self.assertIn("crisis_assessment", payload["briefing"])
        self.assertEqual(payload["state"]["scenario_id"], "central-london-relief-demo")

    def test_plan_does_not_mutate_operational_state(self) -> None:
        with patch("app.services.planner.planning_service._assignment_solver", fake_assignment_solver):
            response = TestClient(app).post("/plan", json={"objective": "Prioritize urgent evacuation."})

        convoy = next(item for item in response.json()["state"]["convoys"] if item["convoy_id"] == "convoy-1")
        self.assertEqual(convoy["status"], "STAGING")
        self.assertIsNone(convoy["current_request_id"])
