"""Simulate disruption events and trigger autonomous replanning."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.llm_client import llm_client
from app.schemas.relief import (
    DisruptionReplan,
    Hazard,
    HazardType,
    ObjectiveCommand,
    ObjectiveAction,
    PlanningResponse,
    ReasoningLogEntry,
)
from app.services.engine_client import EngineClientError, compute_routes_for_assignments
from app.services.planner import planning_service
from app.services.ops_broadcaster import operations_broadcaster
from app.services.state_store import state_store

ENGINE_SERVICE_PATH = Path(__file__).resolve().parents[3] / "engine-service"


class EventInjector:
    """Simulate a bridge/road collapse, update graph, and trigger autonomous replan."""

    async def inject_bridge_collapse(self) -> PlanningResponse | None:
        # 1. Mutate the road graph in-memory to block the specific edge
        engine_path = str(ENGINE_SERVICE_PATH)
        if engine_path not in sys.path:
            sys.path.insert(0, engine_path)

        from src.graph_loader import load_graph
        try:
            graph = load_graph()
            edge_id_to_block = "108275:2620932404:0"
            for u, v, k, data in graph.edges(keys=True, data=True):
                if data.get("edge_id") == edge_id_to_block:
                    data["blocked"] = True
                    data["status"] = "BLOCKED"
        except Exception:
            # Graph not loaded/available, proceed with state mutation anyway
            pass

        # 2. Add the collapse hazard to the state store
        hazard = Hazard(
            hazard_id="haz-bridge-7-collapse",
            edge_ids=["108275:2620932404:0"],
            type=HazardType.COLLAPSE,
            severity=5,
        )
        try:
            state_store.add_hazard(hazard)
        except Exception:
            # Hazard already exists or state store error, proceed
            pass

        state = state_store.get_state()

        # 3. Retrieve prior planning response (auto-generate if missing)
        prior_response = getattr(planning_service, "_last_planning_response", None)
        if not prior_response:
            from app.schemas.relief import ObjectivePlanRequest
            default_request = ObjectivePlanRequest(
                objective="Deliver medical supplies to Sector 4 and prioritize evacuating the shelter on Elm Street before nightfall."
            )
            prior_response = planning_service.plan(default_request)

        # 4. Generate fallback replan based on deterministic solver
        state_payload = state.model_dump(mode="json")
        solver_assignments = planning_service._assignment_solver(
            state_payload["convoys"], state_payload["requests"]
        )
        deterministic_actions = [
            ObjectiveAction.model_validate(assignment.to_action())
            for assignment in solver_assignments
        ]
        
        now = datetime.now(timezone.utc)
        fallback_replan = DisruptionReplan(
            command=ObjectiveCommand(
                command_id=f"replan-{uuid4()}",
                raw_input_text=prior_response.command.raw_input_text,
                interpreted_actions=deterministic_actions,
            ),
            briefing=planning_service._briefing(
                state,
                deterministic_actions,
                prior_response.command.raw_input_text,
                now,
            ),
            change_summary="Bridge 7 collapse detected. Rerouting Convoy 1 to avoid the blocked road.",
        )

        # 5. Call LLM for disruption replanning (or fallback to deterministic)
        disruption_description = "Bridge 7 has collapsed on the main access corridor, blocking key routes."
        replan = llm_client.replan_after_disruption(
            disruption_description,
            prior_response.command,
            state,
            fallback_replan,
        )

        # 6. Compute routes for revised assignments
        try:
            routes = compute_routes_for_assignments(state, replan.command.interpreted_actions)
        except EngineClientError:
            replan = fallback_replan
            routes = [planning_service._route_response(a) for a in solver_assignments]

        # 7. Append new reasoning log entries
        reasoning_log = [
            ReasoningLogEntry(
                timestamp=now,
                message=f"Disruption detected: {disruption_description}",
            ),
            ReasoningLogEntry(
                timestamp=now,
                message=replan.change_summary,
            ),
            ReasoningLogEntry(
                timestamp=now,
                message=f"Re-computed routing for {len(routes)} convoys.",
            ),
        ]
        new_reasoning_log = list(prior_response.reasoning_log) + reasoning_log

        new_response = PlanningResponse(
            command=replan.command,
            routes=routes,
            briefing=replan.briefing,
            reasoning_log=new_reasoning_log,
            state=state,
        )

        # Cache the new response as the latest plan
        planning_service._last_planning_response = new_response

        # 8. Broadcast updated plan over WebSocket
        await operations_broadcaster.broadcast_snapshot(
            state.model_dump(mode="json"),
            [r.model_dump(mode="json") for r in routes],
            replan.briefing.model_dump(mode="json"),
            [log.model_dump(mode="json") for log in new_reasoning_log],
        )

        return new_response

    async def inject_flood_surge(self) -> PlanningResponse | None:
        # 1. Mutate the road graph in-memory to block the specific edge
        engine_path = str(ENGINE_SERVICE_PATH)
        if engine_path not in sys.path:
            sys.path.insert(0, engine_path)

        from src.graph_loader import load_graph
        try:
            graph = load_graph()
            edge_id_to_block = "1270370717:108277:0"
            for u, v, k, data in graph.edges(keys=True, data=True):
                if data.get("edge_id") == edge_id_to_block:
                    data["blocked"] = True
                    data["status"] = "BLOCKED"
        except Exception:
            # Graph not loaded/available, proceed
            pass

        # 2. Add the flood hazard to the state store
        hazard = Hazard(
            hazard_id="haz-river-flood-surge",
            edge_ids=["1270370717:108277:0"],
            type=HazardType.FLOOD,
            severity=5,
        )
        try:
            state_store.add_hazard(hazard)
        except Exception:
            # Already exists or state store error, proceed
            pass

        state = state_store.get_state()

        # 3. Retrieve prior planning response (auto-generate if missing)
        prior_response = getattr(planning_service, "_last_planning_response", None)
        if not prior_response:
            from app.schemas.relief import ObjectivePlanRequest
            default_request = ObjectivePlanRequest(
                objective="Deliver medical supplies to Sector 4 and prioritize evacuating the shelter on Elm Street before nightfall."
            )
            prior_response = planning_service.plan(default_request)

        # 4. Generate fallback replan based on deterministic solver
        state_payload = state.model_dump(mode="json")
        solver_assignments = planning_service._assignment_solver(
            state_payload["convoys"], state_payload["requests"]
        )
        deterministic_actions = [
            ObjectiveAction.model_validate(assignment.to_action())
            for assignment in solver_assignments
        ]
        
        now = datetime.now(timezone.utc)
        fallback_replan = DisruptionReplan(
            command=ObjectiveCommand(
                command_id=f"replan-{uuid4()}",
                raw_input_text=prior_response.command.raw_input_text,
                interpreted_actions=deterministic_actions,
            ),
            briefing=planning_service._briefing(
                state,
                deterministic_actions,
                prior_response.command.raw_input_text,
                now,
            ),
            change_summary="River flood surge detected. Rerouting Convoy 1 away from the Embankment.",
        )

        # 5. Call LLM for disruption replanning (or fallback to deterministic)
        disruption_description = "A river flood surge has occurred near the Embankment, closing key transit points."
        replan = llm_client.replan_after_disruption(
            disruption_description,
            prior_response.command,
            state,
            fallback_replan,
        )

        # 6. Compute routes for revised assignments
        try:
            routes = compute_routes_for_assignments(state, replan.command.interpreted_actions)
        except EngineClientError:
            replan = fallback_replan
            routes = [planning_service._route_response(a) for a in solver_assignments]

        # 7. Append new reasoning log entries
        reasoning_log = [
            ReasoningLogEntry(
                timestamp=now,
                message=f"Disruption detected: {disruption_description}",
            ),
            ReasoningLogEntry(
                timestamp=now,
                message=replan.change_summary,
            ),
            ReasoningLogEntry(
                timestamp=now,
                message=f"Re-computed routing for {len(routes)} convoys.",
            ),
        ]
        new_reasoning_log = list(prior_response.reasoning_log) + reasoning_log

        new_response = PlanningResponse(
            command=replan.command,
            routes=routes,
            briefing=replan.briefing,
            reasoning_log=new_reasoning_log,
            state=state,
        )

        # Cache the new response as the latest plan
        planning_service._last_planning_response = new_response

        # 8. Broadcast updated plan over WebSocket
        await operations_broadcaster.broadcast_snapshot(
            state.model_dump(mode="json"),
            [r.model_dump(mode="json") for r in routes],
            replan.briefing.model_dump(mode="json"),
            [log.model_dump(mode="json") for log in new_reasoning_log],
        )

        return new_response


event_injector = EventInjector()
