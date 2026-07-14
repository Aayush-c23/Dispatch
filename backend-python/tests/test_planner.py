"""Tests for complete structured Mission Briefings in planning responses."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.core.llm_client import LLMClient
from app.schemas.relief import (
    ConfidenceLevel,
    ConvoyAssignment,
    MissionBriefing,
    ObjectivePlanRequest,
)
from app.services.planner import PlanningService
from app.services.state_store import OperationalStateStore


def fake_assignment_solver(_convoys: list[dict[str, object]], _requests: list[dict[str, object]]) -> list[SimpleNamespace]:
    route = SimpleNamespace(
        origin_node=100,
        destination_node=200,
        node_ids=[100, 200],
        edge_ids=["100-200"],
        geometry=[{"lat": 51.5014, "lon": -0.1419}, {"lat": 51.5056, "lon": -0.1356}],
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


class BriefingLLM:
    def __init__(self, briefing: MissionBriefing) -> None:
        self.briefing = briefing
        self.briefing_calls = 0

    def plan_objective(self, _objective: str, _state: object, fallback: object) -> object:
        return fallback

    def generate_briefing(
        self, _objective: str, _state: object, _command: object, _fallback: MissionBriefing
    ) -> MissionBriefing:
        self.briefing_calls += 1
        return self.briefing


class PlanningServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = OperationalStateStore()
        self.request = ObjectivePlanRequest(objective="Prioritize the Elm Street evacuation.")

    def test_no_key_plan_returns_complete_structured_fallback_briefing(self) -> None:
        service = PlanningService(
            store=self.store,
            assignment_solver=fake_assignment_solver,
            llm=LLMClient(api_key=None),
        )

        response = service.plan(self.request)

        briefing = response.briefing.model_dump(mode="json")
        self.assertTrue(briefing["crisis_assessment"])
        self.assertTrue(briefing["highest_risk_areas"])
        self.assertTrue(briefing["convoy_assignments"])
        self.assertTrue(briefing["predicted_bottlenecks"])
        self.assertIn(briefing["confidence_level"], {"HIGH", "MEDIUM", "LOW"})
        self.assertTrue(briefing["backup_plan"])

    def test_uses_valid_llm_briefing_with_structured_fields(self) -> None:
        llm_briefing = MissionBriefing(
            briefing_id="llm-briefing",
            timestamp=datetime.now(timezone.utc),
            crisis_assessment="Elm Street evacuation is the immediate priority.",
            convoy_assignments=[
                ConvoyAssignment(
                    convoy_id="convoy-1",
                    request_id="req-evac-elm-shelter",
                    rationale="Fastest feasible evacuation response.",
                )
            ],
            confidence_level=ConfidenceLevel.HIGH,
            backup_plan="Hold convoy-2 for the medical request.",
        )
        llm = BriefingLLM(llm_briefing)
        service = PlanningService(
            store=self.store,
            assignment_solver=fake_assignment_solver,
            llm=llm,  # type: ignore[arg-type]
        )

        response = service.plan(self.request)

        self.assertEqual(response.briefing.briefing_id, "llm-briefing")
        self.assertEqual(llm.briefing_calls, 1)
        self.assertIn("structured Mission Briefing", response.reasoning_log[-1].message)
