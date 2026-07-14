"""Deterministic objective planning used until LLM orchestration is enabled."""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.llm_client import LLMClient, llm_client
from app.schemas.relief import (
    ActionType,
    ConfidenceLevel,
    ConvoyAssignment,
    HighestRiskArea,
    MissionBriefing,
    ObjectiveAction,
    ObjectiveCommand,
    ObjectivePlanRequest,
    OperationalState,
    PlanningResponse,
    PredictedBottleneck,
    ReasoningLogEntry,
    RouteResponse,
)
from app.services.engine_client import EngineClientError, compute_routes_for_assignments
from app.services.state_store import OperationalStateStore, state_store

ENGINE_SERVICE_PATH = Path(__file__).resolve().parents[3] / "engine-service"
AssignmentSolver = Callable[[list[dict[str, Any]], list[dict[str, Any]]], list[Any]]


def _default_assignment_solver(
    convoys: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> list[Any]:
    """Load the engine policy lazily to preserve the backend/engine boundary."""

    engine_path = str(ENGINE_SERVICE_PATH)
    if engine_path not in sys.path:
        sys.path.insert(0, engine_path)

    from src.assignment_solver import solve_assignments

    return solve_assignments(convoys, requests)


class PlanningService:
    """Create a schema-valid plan and Mission Briefing from one state snapshot.

    Planning deliberately does not assign convoys in the state store. Executing
    approved actions is a separate workflow, so repeated requests remain safe
    and reproducible while the LLM planner is introduced in the next phase.
    """

    def __init__(
        self,
        store: OperationalStateStore = state_store,
        assignment_solver: AssignmentSolver = _default_assignment_solver,
        llm: LLMClient = llm_client,
    ) -> None:
        self._store = store
        self._assignment_solver = assignment_solver
        self._llm = llm
        self._last_planning_response: PlanningResponse | None = None

    def plan(self, request: ObjectivePlanRequest) -> PlanningResponse:
        state = self._store.get_state()
        state_payload = state.model_dump(mode="json")
        solver_assignments = self._assignment_solver(
            state_payload["convoys"], state_payload["requests"]
        )
        deterministic_actions = [
            ObjectiveAction.model_validate(assignment.to_action())
            for assignment in solver_assignments
        ]
        now = datetime.now(timezone.utc)
        deterministic_command = ObjectiveCommand(
            command_id=f"plan-{uuid4()}",
            raw_input_text=request.objective,
            interpreted_actions=deterministic_actions,
        )
        command = self._llm.plan_objective(request.objective, state, deterministic_command)
        if not self._actions_reference_current_state(command.interpreted_actions, state):
            command = deterministic_command

        if command is deterministic_command:
            routes = [self._route_response(assignment) for assignment in solver_assignments]
        else:
            try:
                routes = compute_routes_for_assignments(state, command.interpreted_actions)
            except EngineClientError:
                command = deterministic_command
                routes = [self._route_response(assignment) for assignment in solver_assignments]

        fallback_briefing = self._briefing(
            state, command.interpreted_actions, request.objective, now
        )
        briefing = self._llm.generate_briefing(
            request.objective,
            state,
            command,
            fallback_briefing,
        )
        if not self._briefing_references_current_state(briefing, state):
            briefing = fallback_briefing

        response = PlanningResponse(
            command=command,
            routes=routes,
            briefing=briefing,
            reasoning_log=self._reasoning_log(
                state,
                command.interpreted_actions,
                now,
                used_llm=command is not deterministic_command,
                used_llm_briefing=briefing is not fallback_briefing,
            ),
            state=state,
        )
        self._store.save_plan(
            routes=[route.model_dump(mode="json") for route in response.routes],
            briefing=response.briefing.model_dump(mode="json"),
            reasoning_log=[log.model_dump(mode="json") for log in response.reasoning_log],
        )
        self._last_planning_response = response
        return response

    @staticmethod
    def _actions_reference_current_state(
        actions: list[ObjectiveAction], state: OperationalState
    ) -> bool:
        convoy_ids = {convoy.convoy_id for convoy in state.convoys}
        request_ids = {request.request_id for request in state.requests}
        for action in actions:
            if action.target_convoy_id not in convoy_ids:
                return False
            if action.action_type in {ActionType.ASSIGN, ActionType.REROUTE}:
                if action.target_request_id not in request_ids:
                    return False
        return True

    @staticmethod
    def _briefing_references_current_state(
        briefing: MissionBriefing, state: OperationalState
    ) -> bool:
        convoy_ids = {convoy.convoy_id for convoy in state.convoys}
        request_ids = {request.request_id for request in state.requests}
        return all(
            assignment.convoy_id in convoy_ids and assignment.request_id in request_ids
            for assignment in briefing.convoy_assignments
        )

    @staticmethod
    def _route_response(assignment: Any) -> RouteResponse:
        route = assignment.route
        return RouteResponse(
            convoy_id=assignment.convoy_id,
            request_id=assignment.request_id,
            origin_node=route.origin_node,
            destination_node=route.destination_node,
            node_ids=route.node_ids,
            edge_ids=route.edge_ids,
            geometry=route.geometry,
            distance_meters=route.distance_meters,
            estimated_seconds=route.estimated_seconds,
        )

    @staticmethod
    def _briefing(
        state: OperationalState,
        actions: list[ObjectiveAction],
        objective: str,
        timestamp: datetime,
    ) -> MissionBriefing:
        assignments = [
            ConvoyAssignment(
                convoy_id=action.target_convoy_id,
                request_id=action.target_request_id,
                rationale=action.rationale,
            )
            for action in actions
            if action.target_request_id is not None
        ]
        highest_priority = sorted(
            state.requests,
            key=lambda item: (-item.priority, -item.population_affected, item.request_id),
        )[:2]
        risk_areas = [
            HighestRiskArea(
                lat=item.lat,
                lon=item.lon,
                description=(
                    f"Priority {item.priority} {item.type.value.lower()} request "
                    f"affecting {item.population_affected} people."
                ),
            )
            for item in highest_priority
        ]
        unassigned_open_requests = [
            item for item in state.requests
            if item.status.value == "OPEN" and item.request_id not in {a.request_id for a in assignments}
        ]
        bottlenecks = [
            PredictedBottleneck(
                location="Central London road network",
                description=(
                    f"{hazard.type.value.replace('_', ' ').title()} hazard "
                    f"{hazard.hazard_id} affects {len(hazard.edge_ids)} monitored road segment(s)."
                ),
            )
            for hazard in state.hazards
        ]
        if unassigned_open_requests:
            backup_plan = (
                "Hold remaining staging capacity for "
                f"{unassigned_open_requests[0].request_id} if a convoy becomes available."
            )
        else:
            backup_plan = "Monitor hazards and retain the next available convoy for any new urgent request."

        return MissionBriefing(
            briefing_id=f"briefing-{uuid4()}",
            timestamp=timestamp,
            crisis_assessment=(
                f"Deterministic plan prepared for objective: {objective}. "
                f"{len(assignments)} convoy assignment(s) are currently feasible."
            ),
            highest_risk_areas=risk_areas,
            convoy_assignments=assignments,
            predicted_bottlenecks=bottlenecks,
            confidence_level=(
                ConfidenceLevel.HIGH if not unassigned_open_requests else ConfidenceLevel.MEDIUM
            ),
            backup_plan=backup_plan,
        )

    @staticmethod
    def _reasoning_log(
        state: OperationalState,
        actions: list[ObjectiveAction],
        timestamp: datetime,
        used_llm: bool,
        used_llm_briefing: bool,
    ) -> list[ReasoningLogEntry]:
        logs = [
            ReasoningLogEntry(
                timestamp=timestamp,
                message=(
                    "GPT-5.6 returned a schema-valid plan."
                    if used_llm
                    else "Deterministic assignment solver selected; OpenAI was not used."
                ),
            ),
            ReasoningLogEntry(
                timestamp=timestamp,
                message=(
                    f"Evaluated {len(state.convoys)} convoys against "
                    f"{len(state.requests)} requests using the assignment solver."
                ),
            ),
            ReasoningLogEntry(
                timestamp=timestamp,
                message=f"Produced {len(actions)} feasible convoy assignment(s) and route(s).",
            )
        ]
        
        for action in actions:
            if action.action_type in {ActionType.ASSIGN, ActionType.REROUTE} and action.rationale:
                logs.append(
                    ReasoningLogEntry(
                        timestamp=timestamp,
                        message=f"[ETA Solver] Convoy '{action.target_convoy_id}': {action.rationale}"
                    )
                )

        logs.append(
            ReasoningLogEntry(
                timestamp=timestamp,
                message=(
                    "GPT-5.6 generated the structured Mission Briefing."
                    if used_llm_briefing
                    else "Deterministic Mission Briefing fallback selected."
                ),
            )
        )
        return logs


planning_service = PlanningService()
