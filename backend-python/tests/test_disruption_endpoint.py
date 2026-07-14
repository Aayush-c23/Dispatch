"""Contract tests for the disruption event injection and autonomous replanning endpoints."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

try:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.planner import planning_service
    from app.services.state_store import state_store
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
                "rationale": "Rerouted / Assigned convoy to shelter.",
            },
        )
    ]


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed in this environment.")
class DisruptionEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        # Reset planning service state and state store hazards
        planning_service._last_planning_response = None
        state = state_store.get_state()
        state.hazards = [h for h in state.hazards if h.hazard_id != "haz-bridge-7-collapse"]
        state_store._state = state

    @patch("app.services.ops_broadcaster.operations_broadcaster.broadcast_snapshot", new_callable=AsyncMock)
    def test_disruption_auto_generates_baseline_plan_if_missing(self, mock_broadcast: AsyncMock) -> None:
        client = TestClient(app)
        response = client.post("/events/bridge-collapse")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(h["hazard_id"] == "haz-bridge-7-collapse" for h in payload["state"]["hazards"]))

    @patch("app.services.ops_broadcaster.operations_broadcaster.broadcast_snapshot", new_callable=AsyncMock)
    def test_disruption_triggers_replanning_and_broadcast(self, mock_broadcast: AsyncMock) -> None:
        client = TestClient(app)

        # 1. Create a prior plan
        with patch("app.services.planner.planning_service._assignment_solver", fake_assignment_solver):
            plan_response = client.post("/plan", json={"objective": "Test objective"})
            self.assertEqual(plan_response.status_code, 200)

        # 2. Simulate disruption
        with patch("app.services.planner.planning_service._assignment_solver", fake_assignment_solver):
            disruption_response = client.post("/events/bridge-collapse")
            self.assertEqual(disruption_response.status_code, 200)

        # 3. Verify state contains new hazard
        payload = disruption_response.json()
        self.assertTrue(any(h["hazard_id"] == "haz-bridge-7-collapse" for h in payload["state"]["hazards"]))

        # 4. Verify broadcast was called
        mock_broadcast.assert_called()

        # 5. Verify reasoning log appended disruption details
        log_messages = [log["message"] for log in payload["reasoning_log"]]
        self.assertTrue(any("Disruption detected" in msg for msg in log_messages))
