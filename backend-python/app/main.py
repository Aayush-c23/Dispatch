"""FastAPI entrypoint for the ReliefGrid AI orchestration backend."""

from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.llm_client import llm_client
from pydantic import BaseModel

from app.schemas.relief import (
    ObjectivePlanRequest,
    PlanningResponse,
    OperationalQueryRequest,
    OperationalQueryResponse,
    SpatialObstructionRequest,
)

class RouteSelectionRequest(BaseModel):
    convoy_id: str
    label: str

from app.services.planner import planning_service
from app.services.ops_broadcaster import operations_broadcaster
from app.services.state_store import state_store
from app.services.event_injector import event_injector
from app.services.live_context import live_context_service
from app.services.simulator import transit_simulator

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI orchestration layer for humanitarian logistics planning.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "online",
        "service": "reliefgrid-ai-orchestration",
        "version": settings.app_version,
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
        "model": settings.active_llm_model,
        "llm_configured": bool(settings.active_llm_api_key),
    }


@app.post("/plan", response_model=PlanningResponse)
async def plan(request: ObjectivePlanRequest) -> PlanningResponse:
    """Produce a deterministic, non-mutating operational plan for an objective."""

    response = planning_service.plan(request)
    await operations_broadcaster.broadcast_snapshot({
        "state": response.state.model_dump(mode="json"),
        "routes": [route.model_dump(mode="json") for route in response.routes],
        "briefing": response.briefing.model_dump(mode="json"),
        "reasoning_log": [log.model_dump(mode="json") for log in response.reasoning_log],
    })
    return response


@app.post("/events/bridge-collapse", response_model=PlanningResponse)
async def trigger_bridge_collapse() -> PlanningResponse:
    """Simulate a bridge collapse event, triggering autonomous replanning."""

    response = await event_injector.inject_bridge_collapse()
    return response


@app.post("/query", response_model=OperationalQueryResponse)
async def query_ops(request: OperationalQueryRequest) -> OperationalQueryResponse:
    """Answer an operational question grounded in the live state."""

    state = state_store.get_state()
    return llm_client.answer_operational_query(request.question, state)


@app.get("/live-context")
async def get_live_context() -> dict[str, Any]:
    """Retrieve current weather conditions and global RSS disaster alerts."""

    weather = await live_context_service.fetch_weather()
    alerts = await live_context_service.fetch_gdacs_alerts()
    return {
        "weather": weather,
        "alerts": alerts,
    }


@app.post("/events/flood-surge", response_model=PlanningResponse)
async def trigger_flood_surge() -> PlanningResponse:
    """Simulate a river flood surge, triggering autonomous replanning."""

    response = await event_injector.inject_flood_surge()
    return response


@app.post("/events/obstruction", response_model=PlanningResponse)
async def trigger_obstruction(request: SpatialObstructionRequest) -> PlanningResponse:
    """Inject a spatial physical obstruction and trigger dynamic live rerouting."""

    response = await event_injector.inject_obstruction(
        lat=request.lat,
        lon=request.lon,
        radius_meters=request.radius_meters,
        hazard_type=request.hazard_type,
        severity=request.severity,
    )
    return response


@app.post("/transit/start")
async def start_transit() -> dict[str, str]:
    """Start the server-side transit simulation for assigned convoys."""
    transit_simulator.start()
    return {"status": "started"}


@app.post("/routes/select")
async def select_route(request: RouteSelectionRequest) -> dict[str, str]:
    """Select a specific alternate route as primary for a convoy."""
    state_store.select_primary_route(request.convoy_id, request.label)
    # Broadcast updated state so clients re-render
    await operations_broadcaster.broadcast_snapshot(state_store.snapshot())
    return {"status": "ok"}

@app.websocket("/ws/ops")
async def ops_websocket(websocket: WebSocket) -> None:
    """Stream the current operational snapshot and subsequent state updates."""

    await operations_broadcaster.connect(websocket, state_store.snapshot())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        operations_broadcaster.disconnect(websocket)
