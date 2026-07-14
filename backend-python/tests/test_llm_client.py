"""Focused tests for schema-enforced LLM planning and fallbacks."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.core.llm_client import LLMClient
from app.schemas.relief import (
    ActionType,
    ConfidenceLevel,
    ConvoyAssignment,
    DisruptionReplan,
    MissionBriefing,
    ObjectiveAction,
    ObjectiveCommand,
    OperationalQueryResponse,
)
from app.services.state_store import build_seed_state


class FakeResponses:
    def __init__(self, outputs: list[object]) -> None:
        self.outputs = outputs
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return SimpleNamespace(output_parsed=output)


class LLMClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = build_seed_state()
        self.fallback_command = ObjectiveCommand(
            command_id="deterministic-plan",
            raw_input_text="Prioritize evacuation.",
            interpreted_actions=[
                ObjectiveAction(
                    target_convoy_id="convoy-1",
                    action_type=ActionType.ASSIGN,
                    target_request_id="req-evac-elm-shelter",
                    priority_score=5,
                    rationale="Deterministic fallback.",
                )
            ],
        )
        self.fallback_briefing = MissionBriefing(
            briefing_id="deterministic-briefing",
            timestamp=datetime.now(timezone.utc),
            crisis_assessment="Deterministic fallback briefing.",
            convoy_assignments=[
                ConvoyAssignment(
                    convoy_id="convoy-1",
                    request_id="req-evac-elm-shelter",
                    rationale="Deterministic fallback.",
                )
            ],
            confidence_level=ConfidenceLevel.MEDIUM,
            backup_plan="Hold remaining capacity.",
        )

    def test_no_key_returns_deterministic_plan_without_calling_sdk(self) -> None:
        client = LLMClient(api_key=None)

        result = client.plan_objective("Prioritize evacuation.", self.state, self.fallback_command)

        self.assertEqual(result, self.fallback_command)

    def test_valid_structured_outputs_are_parsed_for_all_llm_operations(self) -> None:
        llm_plan = self.fallback_command.model_copy(update={"command_id": "llm-plan"})
        llm_briefing = self.fallback_briefing.model_copy(update={"briefing_id": "llm-briefing"})
        replan = DisruptionReplan(
            command=llm_plan,
            briefing=llm_briefing,
            change_summary="Flood risk requires a revised route.",
        )
        responses = FakeResponses([llm_plan, llm_briefing, replan, OperationalQueryResponse(answer="Two priority-five requests remain open.")])
        client = LLMClient(api_key="test-key", client=SimpleNamespace(responses=responses))

        self.assertEqual(client.plan_objective("Prioritize evacuation.", self.state, self.fallback_command).command_id, "llm-plan")
        self.assertEqual(client.generate_briefing("Prioritize evacuation.", self.state, llm_plan, self.fallback_briefing).briefing_id, "llm-briefing")
        self.assertEqual(client.replan_after_disruption("Flood risk", llm_plan, self.state, replan).change_summary, replan.change_summary)
        self.assertIn("priority-five", client.answer_operational_query("What is urgent?", self.state).answer)
        self.assertTrue(all(call["model"] == "gpt-5.6" for call in responses.calls))

    def test_malformed_model_output_uses_deterministic_fallback(self) -> None:
        responses = FakeResponses([{"command_id": "bad", "raw_input_text": "x", "interpreted_actions": [{"target_convoy_id": "convoy-1", "action_type": "ASSIGN", "priority_score": 9, "rationale": "invalid"}]}])
        client = LLMClient(api_key="test-key", client=SimpleNamespace(responses=responses))

        result = client.plan_objective("Prioritize evacuation.", self.state, self.fallback_command)

        self.assertEqual(result, self.fallback_command)

    def test_api_failure_reuses_last_valid_plan(self) -> None:
        cached_plan = self.fallback_command.model_copy(update={"command_id": "cached-plan"})
        responses = FakeResponses([cached_plan, RuntimeError("temporary API failure")])
        client = LLMClient(api_key="test-key", client=SimpleNamespace(responses=responses))

        client.plan_objective("Prioritize evacuation.", self.state, self.fallback_command)
        result = client.plan_objective("Prioritize medical response.", self.state, self.fallback_command)

        self.assertEqual(result.command_id, "cached-plan")
