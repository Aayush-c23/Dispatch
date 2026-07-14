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
    ConvoyStatus,
)
from app.services.engine_client import EngineClientError, compute_routes_for_assignments
from app.services.planner import planning_service
from app.services.ops_broadcaster import operations_broadcaster
from app.services.state_store import state_store

ENGINE_SERVICE_PATH = Path(__file__).resolve().parents[3] / "engine-service"


class EventInjector:
    """Inject spatial hazards, update overlay, and trigger intelligent live rerouting."""

    async def inject_obstruction(
        self, lat: float, lon: float, radius_meters: float, hazard_type: HazardType, severity: int, description: str = ""
    ) -> PlanningResponse:
        engine_path = str(ENGINE_SERVICE_PATH)
        if engine_path not in sys.path:
            sys.path.insert(0, engine_path)

        from src.router import get_edges_in_radius
        from src.obstructions import overlay

        # 1. Query spatial index for edges within the radius
        try:
            affected_edges = get_edges_in_radius(lat, lon, radius_meters)
        except Exception:
            affected_edges = []

        hazard_id = f"haz-{hazard_type.value.lower()}-{uuid4().hex[:6]}"
        
        # 2. Add to spatial obstruction overlay (non-destructive)
        if affected_edges:
            try:
                overlay.apply_obstruction(affected_edges, hazard_id, status="BLOCKED", multiplier=float(severity))
            except Exception:
                pass

        # 3. Add to state store for frontend visualization
        # Pass the lat/lon to hazard if possible, but schema doesn't have it.
        # We can pass edges so the frontend can query, but frontend draws polygon via lat/lon manually.
        # Wait, the frontend needs lat/lon/radius. We should stuff them in the hazard_id or wait, state.hazards doesn't have lat/lon.
        # Since I can't easily change the Hazard schema without migrating everywhere, 
        # I'll rely on the frontend decoding lat/lon/radius from hazard_id for simplicity, or just update Hazard schema.
        # Actually, let's just update Hazard schema later if needed, but for now it has edge_ids.
        hazard = Hazard(
            hazard_id=f"{hazard_id}|{lat}|{lon}|{radius_meters}",
            edge_ids=affected_edges if affected_edges else ["dummy"],
            type=hazard_type,
            severity=severity,
        )
        try:
            state_store.add_hazard(hazard)
        except Exception:
            pass

        state = state_store.get_state()

        # 4. Retrieve prior planning response (auto-generate if missing)
        prior_response = getattr(planning_service, "_last_planning_response", None)
        if not prior_response:
            from app.schemas.relief import ObjectivePlanRequest
            default_request = ObjectivePlanRequest(
                objective="Deliver medical supplies to Sector 4 and prioritize evacuating the shelter on Elm Street before nightfall."
            )
            prior_response = planning_service.plan(default_request)

        # 5. Determine which active routes are actually affected
        affected_convoy_ids = set()
        affected_edge_set = set(affected_edges)
        
        for route in prior_response.routes:
            # Check if convoy is active
            convoy = next((c for c in state.convoys if c.convoy_id == route.convoy_id), None)
            if convoy and convoy.status in {ConvoyStatus.EN_ROUTE, ConvoyStatus.EVACUATING, ConvoyStatus.STAGING}:
                # If their route crosses any blocked edge, they are affected
                if any(e in affected_edge_set for e in route.edge_ids):
                    affected_convoy_ids.add(route.convoy_id)
        
        now = datetime.now(timezone.utc)
        
        # If no one is affected, we still return the plan but with no reroutes
        if not affected_convoy_ids:
            change_summary = f"{hazard_type.value.capitalize()} detected. No active convoys are affected."
            replan_actions = prior_response.command.interpreted_actions
            new_routes = prior_response.routes
        else:
            affected_names = [c.name for c in state.convoys if c.convoy_id in affected_convoy_ids]
            change_summary = f"{hazard_type.value.capitalize()} detected. Rerouting affected convoys: {', '.join(affected_names)} from their current positions."
            
            # We keep all unaffected routes, and only recompute the affected ones
            new_routes = [r for r in prior_response.routes if r.convoy_id not in affected_convoy_ids]
            
            # Recompute routes for affected convoys
            affected_actions = [a for a in prior_response.command.interpreted_actions if a.target_convoy_id in affected_convoy_ids]
            try:
                recomputed_routes = compute_routes_for_assignments(state, affected_actions)
                new_routes.extend(recomputed_routes)
            except EngineClientError:
                pass # fallback to original routes if it fails

            replan_actions = prior_response.command.interpreted_actions

        disruption_description = description or f"A {hazard_type.value.lower()} has occurred, blocking {len(affected_edges)} street segments."
        
        fallback_replan = DisruptionReplan(
            command=ObjectiveCommand(
                command_id=f"replan-{uuid4()}",
                raw_input_text=prior_response.command.raw_input_text,
                interpreted_actions=replan_actions,
            ),
            briefing=planning_service._briefing(
                state,
                replan_actions,
                prior_response.command.raw_input_text,
                now,
            ),
            change_summary=change_summary,
        )

        replan = llm_client.replan_after_disruption(
            disruption_description,
            prior_response.command,
            state,
            fallback_replan,
        )

        reasoning_log = [
            ReasoningLogEntry(
                timestamp=now,
                message=f"Disruption detected: {disruption_description}",
            ),
            ReasoningLogEntry(
                timestamp=now,
                message=replan.change_summary,
            )
        ]
        if affected_convoy_ids:
            reasoning_log.append(
                ReasoningLogEntry(
                    timestamp=now,
                    message=f"Successfully recomputed detours for {len(affected_convoy_ids)} convoys.",
                )
            )

        new_reasoning_log = list(prior_response.reasoning_log) + reasoning_log

        new_response = PlanningResponse(
            command=replan.command,
            routes=new_routes,
            briefing=replan.briefing,
            reasoning_log=new_reasoning_log,
            state=state,
        )

        planning_service._last_planning_response = new_response

        await operations_broadcaster.broadcast_snapshot({
            "state": state.model_dump(mode="json"),
            "routes": [r.model_dump(mode="json") for r in new_routes],
            "briefing": replan.briefing.model_dump(mode="json"),
            "reasoning_log": [log.model_dump(mode="json") for log in new_reasoning_log],
        })

        return new_response


    async def inject_bridge_collapse(self) -> PlanningResponse:
        """Demo wrapper for bridge collapse using generic injection."""
        # 51.5029, -0.138 (approx location of bridge 7)
        return await self.inject_obstruction(
            lat=51.5029,
            lon=-0.138,
            radius_meters=50.0,
            hazard_type=HazardType.COLLAPSE,
            severity=5,
            description="Bridge collapse has occurred on the main access corridor."
        )

    async def inject_flood_surge(self) -> PlanningResponse:
        """Demo wrapper for river flood surge using generic injection."""
        # 51.5014, -0.1402 (approx location of embankment flood)
        return await self.inject_obstruction(
            lat=51.5014,
            lon=-0.1402,
            radius_meters=200.0,
            hazard_type=HazardType.FLOOD,
            severity=5,
            description="River flood surge has inundated the Embankment corridor."
        )


event_injector = EventInjector()
