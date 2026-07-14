# ReliefGrid AI

ReliefGrid AI is an AI-powered humanitarian crisis response dashboard for emergency logistics coordinators. The MVP is being built for OpenAI Build Week 2026 under the Work and productivity track.

The intended end-to-end demo flow is:

1. A coordinator enters a natural-language operational objective.
2. GPT-5.6 converts the objective into a multi-step convoy plan.
3. The backend generates a structured Mission Briefing.
4. The routing engine computes routes over a real OpenStreetMap road network.
5. The frontend displays the briefing, routes, convoy state, hazards, and operations metrics.
6. A disruption event triggers autonomous replanning and an updated briefing.

This is framed as professional decision-support software for humanitarian logistics teams. It should not use game-like language such as score, player, gameplay, or win condition.

## Build Process

ReliefGrid AI was built substantially during OpenAI Build Week using Codex as the primary development environment. Codex was used to scaffold the repository, implement the React dashboard, build the FastAPI orchestration backend, generate the OSM graph tooling, implement the routing engine, and maintain the implementation handoff plan.

## Current Implementation Status

Completed so far:

- React/Vite frontend scaffold with the target operations dashboard layout.
- MapLibre-based map component with static operational overlays.
- FastAPI backend app with centralized config and verified `/health` endpoint.
- OpenStreetMap road-network fetch script for the Central London demo region.
- Local GraphML road network generated for development/demo use.
- Routing engine graph loader.
- Dijkstra route computation between latitude/longitude points over the OSM graph.
- Engineer handoff document at `IMPLEMENTATION_HANDOFF.md`.

Not implemented yet:

- Convoy assignment solver.
- Pydantic operational schemas.
- Backend state store.
- `/plan` endpoint.
- GPT-5.6 planning and Mission Briefing calls.
- Frontend-to-backend plan wiring.
- WebSocket live state updates.
- Event injector and autonomous disruption replanning.

## Repository Structure

```text
frontend-react/
  React + Vite + MapLibre operations dashboard

backend-python/
  FastAPI orchestration backend

engine-service/
  OSM graph tooling and routing engine

IMPLEMENTATION_HANDOFF.md
  Detailed resume context and remaining implementation plan
```

## Backend Setup

From the repository root:

```powershell
backend-python\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend-python --reload --port 8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

Expected health response:

```json
{
  "status": "online",
  "service": "reliefgrid-ai-orchestration",
  "version": "0.1.0",
  "environment": "local",
  "model": "gpt-5.6",
  "openai_configured": false
}
```

If the backend virtual environment does not exist yet:

```powershell
python -m venv backend-python\.venv
backend-python\.venv\Scripts\python.exe -m pip install -r backend-python\requirements.txt
```

## Frontend Setup

From `frontend-react/`:

```powershell
npm install
npm run dev
```

Expected local URL:

```text
http://localhost:5173
```

## Road-Network Data

The routing engine uses a pre-fetched OpenStreetMap graph, so it has no external map-data dependency during a demonstration. The demo region is Central London, covering a compact area around Westminster, Trafalgar Square, and the River Thames.

From the repository root, create the graph once:

```powershell
python -m pip install -r engine-service/requirements.txt
python engine-service/scripts/fetch_road_network.py
```

This writes:

```text
engine-service/data/road_network.graphml
engine-service/data/road_network.metadata.json
```

Graph data is excluded from version control because it is derived from OpenStreetMap and can be regenerated with the command above.

## Routing Engine Setup

If the engine virtual environment does not exist yet:

```powershell
python -m venv engine-service\.venv
engine-service\.venv\Scripts\python.exe -m pip install -r engine-service\requirements.txt
```

Verify graph loading:

```powershell
$env:PYTHONPATH=(Resolve-Path 'engine-service').Path
engine-service\.venv\Scripts\python.exe -c "from src.graph_loader import load_graph; graph = load_graph(); print(len(graph.nodes), len(graph.edges))"
```

Expected current graph size:

```text
1716 3468
```

Verify route computation:

```powershell
$env:PYTHONPATH=(Resolve-Path 'engine-service').Path
engine-service\.venv\Scripts\python.exe -c "from src.router import route_between_points; route = route_between_points(51.5014, -0.1419, 51.5079, -0.1280); print(route.to_dict())"
```

The verified smoke test route is approximately:

```text
Distance: 1170.3 meters
ETA: 130.9 seconds
Route nodes: 12
Route edges: 11
```

## GPT-5.6 Configuration

The backend config defaults to:

```text
openai_model = "gpt-5.6"
```

Set `OPENAI_API_KEY` in `backend-python/.env` when the LLM planning and Mission Briefing endpoints are implemented.

If GPT-5.6 API access is unavailable at build time, use the closest available current-generation OpenAI reasoning model and document the substitution here before submission.

## Implementation Handoff

For the detailed resume plan, current state, task order, schemas, prompt templates, and demo constraints, read:

```text
IMPLEMENTATION_HANDOFF.md
```

The next planned implementation task is:

```text
Phase 1 Task 4: Convoy Assignment Solver
```
