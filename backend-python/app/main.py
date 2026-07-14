"""FastAPI entrypoint for the ReliefGrid AI orchestration backend."""

from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.llm_client import llm_client
from app.schemas.relief import (
    ObjectivePlanRequest,
    PlanningResponse,
    OperationalQueryRequest,
    OperationalQueryResponse,
)
from app.services.planner import planning_service
from app.services.ops_broadcaster import operations_broadcaster
from app.services.state_store import state_store
from app.services.event_injector import event_injector
from app.services.live_context import live_context_service

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI orchestration layer for humanitarian logistics planning.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
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
        "model": settings.openai_model,
        "openai_configured": bool(settings.openai_api_key),
    }


@app.post("/plan", response_model=PlanningResponse)
async def plan(request: ObjectivePlanRequest) -> PlanningResponse:
    """Produce a deterministic, non-mutating operational plan for an objective."""

    response = planning_service.plan(request)
    await operations_broadcaster.broadcast_snapshot(
        response.state.model_dump(mode="json"),
        [route.model_dump(mode="json") for route in response.routes],
        response.briefing.model_dump(mode="json"),
        [log.model_dump(mode="json") for log in response.reasoning_log],
    )
    return response


@app.post("/events/bridge-collapse", response_model=PlanningResponse)
async def trigger_bridge_collapse() -> PlanningResponse:
    """Simulate a bridge collapse event, triggering autonomous replanning."""

    response = await event_injector.inject_bridge_collapse()
    if response is None:
        raise HTTPException(
            status_code=400,
            detail="No prior plan exists. Please generate a plan before simulating disruption.",
        )
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
    if response is None:
        raise HTTPException(
            status_code=400,
            detail="No prior plan exists. Please generate a plan before simulating disruption.",
        )
    return response


@app.websocket("/ws/ops")
async def ops_websocket(websocket: WebSocket) -> None:
    """Stream the current operational snapshot and subsequent state updates."""

    await operations_broadcaster.connect(websocket, state_store.snapshot())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        operations_broadcaster.disconnect(websocket)
