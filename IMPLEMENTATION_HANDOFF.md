# ReliefGrid AI Implementation Handoff

Last updated: 2026-07-14

This file is the engineering context needed to resume ReliefGrid AI without relying on chat history. It describes the product, architecture, current repo state, verified setup commands, completed work, remaining implementation sequence, and key constraints.

## Project Summary

ReliefGrid AI is a hackathon MVP for OpenAI Build Week 2026, submitted under the Work and productivity track. It is a professional humanitarian logistics decision-support tool for crisis coordinators, not a game or entertainment simulation.

The core demo story is:

1. A coordinator enters a natural-language operational objective.
2. GPT-5.6 converts the objective into a structured multi-step plan.
3. GPT-5.6 generates a structured Mission Briefing before execution.
4. A routing engine computes convoy routes over a real OpenStreetMap road network.
5. The React dashboard shows the briefing, reasoning log, routes, convoys, hazards, and metrics.
6. A deterministic disruption event is triggered during the run.
7. The backend detects the state change, replans automatically without a new user prompt, and produces an updated Mission Briefing explaining what changed and why.

The product must always read as serious operational software. Avoid terms such as player, score, gameplay, win, level, or simulation-for-fun. Use coordinator, operation, convoy, request, hazard, briefing, replan, assignment, route, and confidence.

## Repository Path

Workspace root:

```text
C:\Users\aayus\OneDrive\Documents\Dispatch
```

Primary project directories:

```text
frontend-react/
backend-python/
engine-service/
```

## Required Architecture

The MVP must keep three distinct tiers:

1. Frontend: React + Vite + MapLibre GL JS.
2. AI orchestration backend: Python + FastAPI.
3. Routing engine: separate Python service/module using osmnx/networkx.

Do not collapse the app into one language or one process-only shortcut for the final MVP. It is fine for early local development to import engine modules directly while wiring, but the architecture and code boundaries should remain distinct.

## Current Status

Phase 0 visual scaffold exists in `frontend-react/`. It includes the dark operations dashboard, MapLibre map component, right-side Operations Control panels, Mission Briefing panel, AI Reasoning Log, System Status, and bottom Operations Dashboard chart area.

Phase 1 Task 1 is complete:

- Added `engine-service/scripts/fetch_road_network.py`.
- Configured the demo region as Central London, UK.
- Generated a local OSM road network at `engine-service/data/road_network.graphml`.
- Graph metadata from generation:
  - Nodes: 1716
  - Edges: 3468
  - Generated: 2026-07-14T06:27:31Z
- GraphML and metadata are intentionally ignored by git because they are derived data.
- Added `engine-service/data/.gitkeep`.
- Updated `engine-service/requirements.txt` to include:
  - `osmnx==2.1.0`
  - `networkx==3.6.1`

Phase 1 Task 2 is complete:

- `backend-python/app/main.py` now defines a real FastAPI app.
- `backend-python/app/core/config.py` now centralizes settings.
- `GET /health` returns a verified operational response.
- CORS is enabled for the local Vite frontend origins.
- Backend dependencies were installed successfully into `backend-python/.venv`.

Verified health result:

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

Important note: an attempted local target install into `backend-python/.deps` produced a Windows access-denied import issue for the FastAPI package. Use `backend-python/.venv` for backend work.

Phase 1 Task 3 is complete:

- `engine-service/src/graph_loader.py` loads the saved GraphML graph.
- Edge attributes are normalized for `edge_id`, `status`, `length`, `travel_time`, `hazard_multiplier`, and `blocked`.
- Blocked, closed, or impassable edges are excluded by the routing weight callback.
- `engine-service/src/router.py` computes Dijkstra routes between latitude/longitude points.
- Route results include origin/destination nodes, node IDs, edge IDs, map-ready geometry, distance meters, and estimated seconds.
- Engine dependencies were installed successfully into `engine-service/.venv`.

Verified route result:

```text
Graph: 1716 nodes, 3468 edges
Route: 12 nodes, 11 edges, 12 geometry points
Distance: 1170.3 meters
ETA: 130.9 seconds
Start: {'lat': 51.5011541, 'lon': -0.140452}
End: {'lat': 51.5075476, 'lon': -0.1278268}
```

## Current Git State

There are uncommitted changes from Phase 1 Tasks 1, 2, and 3. Do not revert them.

Expected modified/untracked files include:

```text
.gitignore
README.md
backend-python/app/core/config.py
backend-python/app/main.py
engine-service/data/.gitkeep
engine-service/requirements.txt
engine-service/src/graph_loader.py
engine-service/src/router.py
engine-service/scripts/fetch_road_network.py
IMPLEMENTATION_HANDOFF.md
```

The generated graph files and local dependency folders should remain untracked.

## Local Runtime Notes

The bundled Python used in this Codex desktop workspace is:

```text
C:\Users\aayus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

The backend virtual environment is:

```text
backend-python\.venv
```

The engine dependency target folder from the earlier install attempt is:

```text
engine-service\.deps
```

The engine virtual environment is:

```text
engine-service\.venv
```

The repo `.gitignore` should ignore:

```text
backend-python/.deps/
engine-service/.deps/
engine-service/.venv/
cache/
engine-service/data/*.graphml
engine-service/data/*.geojson
engine-service/data/*.json
!engine-service/data/.gitkeep
```

## How To Verify Current Work

### Verify Backend Health

From the repository root:

```powershell
$env:PYTHONPATH=(Resolve-Path 'backend-python').Path
backend-python\.venv\Scripts\python.exe -c "from starlette.testclient import TestClient; from app.main import app; response = TestClient(app).get('/health'); print(response.status_code); print(response.json())"
```

Expected:

```text
200
```

The response JSON should show `status` as `online` and `model` as `gpt-5.6`.

### Regenerate OSM Road Graph

From the repository root:

```powershell
python -m pip install -r engine-service/requirements.txt
python engine-service/scripts/fetch_road_network.py
```

In this workspace, if regular `python` is unavailable, use:

```powershell
C:\Users\aayus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pip install --target engine-service\.deps -r engine-service\requirements.txt
$env:PYTHONPATH=(Resolve-Path 'engine-service\.deps').Path
C:\Users\aayus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe engine-service\scripts\fetch_road_network.py
```

Expected output files:

```text
engine-service/data/road_network.graphml
engine-service/data/road_network.metadata.json
```

## Implemented Files And Meaning

### Frontend

`frontend-react/src/App.jsx`

Owns the current single-page layout.

`frontend-react/src/components/MapView.jsx`

MapLibre view with static operational overlays. This must later consume live route, convoy, shelter, request, and hazard state from backend/WebSocket.

`frontend-react/src/components/ObjectiveInput.jsx`

Objective panel with sample coordinator objective and Generate Plan button. Later wire to backend planning endpoint.

`frontend-react/src/components/MissionBriefing.jsx`

Structured briefing panel. Later populate from real backend Mission Briefing response.

`frontend-react/src/components/ReasoningLog.jsx`

Terminal-style reasoning log. Later append backend planning/replanning events.

`frontend-react/src/hooks/useWebSocket.js`

Placeholder/live-state hook area for backend WebSocket.

### Backend

`backend-python/app/main.py`

FastAPI entrypoint. Currently provides app metadata, CORS, and `/health`.

`backend-python/app/core/config.py`

Pydantic settings. Reads `.env` if present. Defaults to `openai_model = "gpt-5.6"`.

`backend-python/app/core/llm_client.py`

Still a placeholder. Must become the OpenAI/GPT-5.6 wrapper with schema-enforced calls.

`backend-python/app/schemas/relief.py`

Still a placeholder. Must define the Pydantic models listed in this handoff.

`backend-python/app/services/engine_client.py`

Still a placeholder. Must call or wrap routing engine behavior.

`backend-python/app/services/event_injector.py`

Still a placeholder. Must mutate operational state and trigger replanning.

`backend-python/app/services/analytics.py`

Still a placeholder. Must produce dashboard metrics.

`backend-python/app/services/live_context.py`

Still a placeholder. Later optional Layer B weather/crisis enrichment. Do not make the live demo depend on this.

### Engine

`engine-service/scripts/fetch_road_network.py`

Fetches Central London OSM road graph and writes GraphML.

`engine-service/src/graph_loader.py`

Loads the local GraphML graph and normalizes edge attributes for routing.

`engine-service/src/router.py`

Computes Dijkstra routes between latitude/longitude points and returns route geometry, edge IDs, distance, and ETA.

`engine-service/src/assignment_solver.py`

Still a placeholder. Must assign convoys to requests using priority/capacity/distance heuristics.

## Required Data Schemas

Implement these in `backend-python/app/schemas/relief.py` first, then keep frontend JSON structures and engine payloads aligned.

### Operational State

`ops_state.json`

Fields:

- `scenario_id`
- `timestamp`
- `convoys[]`
- `requests[]`
- `hazards[]`

Convoy fields:

- `convoy_id`
- `name`
- `lat`
- `lon`
- `status`: `STAGING | EN_ROUTE | DELIVERING | EVACUATING | BLOCKED`
- `capacity`
- `current_request_id`

Request fields:

- `request_id`
- `type`: `MEDICAL | EVACUATION | SUPPLY`
- `lat`
- `lon`
- `priority`: integer 1-5
- `status`: `OPEN | ASSIGNED | IN_PROGRESS | COMPLETE`
- `population_affected`

Hazard fields:

- `hazard_id`
- `edge_ids[]`
- `type`: `FLOOD | COLLAPSE | BLOCKED_ROAD`
- `severity`

### Objective Command

`objective_command.json`

Fields:

- `command_id`
- `raw_input_text`
- `interpreted_actions[]`

Action fields:

- `target_convoy_id`
- `action_type`: `ASSIGN | REROUTE | HOLD`
- `target_request_id`
- `priority_score`: integer 1-5
- `rationale`

### Mission Briefing

`mission_briefing.json`

Fields:

- `briefing_id`
- `timestamp`
- `crisis_assessment`
- `highest_risk_areas[]`
- `convoy_assignments[]`
- `predicted_bottlenecks[]`
- `confidence_level`: `HIGH | MEDIUM | LOW`
- `backup_plan`

Highest-risk area fields:

- `lat`
- `lon`
- `description`

Convoy assignment fields:

- `convoy_id`
- `request_id`
- `rationale`

Predicted bottleneck fields:

- `location`
- `description`

## LLM Prompt Templates To Implement

Implement in `backend-python/app/core/llm_client.py`.

### Objective Planning

Input:

- Current ops state summary
- Coordinator free-text objective

Output only valid JSON:

```json
{
  "actions": [
    {
      "convoy_id": "string",
      "action": "ASSIGN|REROUTE|HOLD",
      "request_id": "string",
      "rationale": "short reason"
    }
  ]
}
```

### Mission Briefing Generation

Input:

- Current plan
- Current ops state

Output must match `mission_briefing.json` exactly.

### Disruption Replanning

Input:

- Prior plan
- Description of the changed condition
- Current ops state

Output:

- Updated `actions` array
- New Mission Briefing
- Explicitly state what changed from the prior plan and why inside the natural-language briefing fields.

### Conversational Operational Query

Input:

- Live metrics
- Coordinator question

Output:

- Plain-text operational answer grounded only in live state.
- Do not invent data.

## Remaining Phase 1 Implementation Plan

Follow this order. After each task, report what changed, how it was tested, and what is next.

### Task 3: Routing Engine Graph Loader And Basic Routing

Status: complete.

Goal: Load the saved OSM GraphML and compute routes between two latitude/longitude points.

Implementation:

- Update `engine-service/src/graph_loader.py`.
- Load `engine-service/data/road_network.graphml` with osmnx/networkx.
- Normalize node coordinates and edge attributes.
- Treat blocked edges as unusable.
- Use `travel_time` or `length` as route weight.
- Update `engine-service/src/router.py`.
- Provide a function like `route_between_points(origin_lat, origin_lon, dest_lat, dest_lon)`.
- Snap coordinates to nearest graph nodes using a direct nearest-node scan for this compact graph.
- Return route geometry as ordered `[lat, lon]` or GeoJSON coordinates, distance meters, estimated travel time seconds, and edge IDs.

Verification:

- Run a script/import check that loads the graph.
- Route between two known Central London coordinates.
- Confirm a non-empty path, distance, ETA, and geometry.

Verified command:

```powershell
$env:PYTHONPATH=(Resolve-Path 'engine-service').Path
engine-service\.venv\Scripts\python.exe -c "from src.graph_loader import load_graph; from src.router import route_between_points; graph = load_graph(); route = route_between_points(51.5014, -0.1419, 51.5079, -0.1280); result = route.to_dict(); print(len(graph.nodes), len(graph.edges)); print(len(result['node_ids']), len(result['edge_ids']), len(result['geometry'])); print(result['distance_meters'], result['estimated_seconds']); print(result['geometry'][0], result['geometry'][-1])"
```

Verified output:

```text
1716 3468
12 11 12
1170.3 130.9
{'lat': 51.5011541, 'lon': -0.140452} {'lat': 51.5075476, 'lon': -0.1278268}
```

### Task 4: Convoy Assignment Solver

Goal: Map convoys to requests using deterministic heuristics before adding LLM orchestration.

Implementation:

- Update `engine-service/src/assignment_solver.py`.
- Inputs: convoys, requests, graph/router.
- Prioritize higher request priority, larger affected population, and feasible convoy capacity.
- Use route time as the cost when available.
- Return assignments compatible with objective actions.

Verification:

- Create a tiny in-code sample state.
- Confirm open high-priority request gets assigned first.
- Confirm unavailable or blocked convoys are skipped.

### Task 5: Backend Schemas

Goal: Lock the Pydantic contracts.

Implementation:

- Fill `backend-python/app/schemas/relief.py`.
- Include enums for convoy status, request type/status, hazard type, action type, confidence level.
- Include models for operational state, objective command, mission briefing, planning responses, route responses, and disruption event requests.
- Use strict validation for priority scores and severity where sensible.

Verification:

- Instantiate sample states and briefing objects.
- Confirm invalid enum values fail validation.

### Task 6: Backend Engine Client

Goal: Let FastAPI call the routing layer.

Implementation:

- Update `backend-python/app/services/engine_client.py`.
- For MVP speed, it can import engine modules directly by path while preserving the service boundary in code.
- Expose a function to compute routes for a set of convoy assignments.
- Return route data ready for frontend MapLibre rendering.

Verification:

- Use sample ops state and assignments.
- Confirm route payloads are returned for assigned convoy/request pairs.

### Task 7: Operational State Store

Goal: Give the backend a live scenario state to plan against.

Implementation:

- Add a simple in-memory state manager, likely `backend-python/app/services/state_store.py`.
- Seed realistic Central London convoys, shelters/requests, and hazards.
- Keep IDs stable for demo reproducibility.
- Include functions to get state, update convoy assignment, add hazard, update request status, and snapshot for WebSocket.

Verification:

- Import state store and confirm seed state validates with Pydantic schemas.

### Task 8: Planning Endpoint Without LLM Fallback

Goal: Wire the first end-to-end backend flow with deterministic planning fallback.

Implementation:

- Add `POST /plan`.
- Input: free-text objective.
- Use deterministic assignment solver first if no OpenAI key is configured.
- Preserve the output shape expected from the later LLM planner.
- Return actions, computed routes, briefing placeholder, reasoning log entries, and current state.

Verification:

- Call endpoint with sample objective.
- Confirm response includes actions, routes, briefing, and state.

### Task 9: GPT-5.6 LLM Client

Goal: Replace/augment deterministic planning with GPT-5.6 schema-enforced reasoning.

Implementation:

- Update `backend-python/app/core/llm_client.py`.
- Use `OPENAI_API_KEY` from settings.
- Default model: `gpt-5.6`.
- If `gpt-5.6` is not available at build time, use the closest available current-generation OpenAI reasoning model and document the substitution in README.
- Implement objective planning, Mission Briefing generation, disruption replanning, and operational query methods.
- Validate all structured model outputs with Pydantic.
- On LLM failure, return cached last valid plan/briefing or deterministic fallback.

Verification:

- Test no-key path does not crash.
- If API key exists, test each call with small sample state.
- Confirm malformed model JSON is rejected and fallback is used.

### Task 10: Real Mission Briefing Generation

Goal: Make Mission Briefing the centerpiece of the backend response.

Implementation:

- After planning, call briefing generation.
- Ensure the UI never receives raw JSON-only text; it should receive structured fields.
- Include assessment, highest-risk areas, assignments, bottlenecks, confidence, and backup plan.

Verification:

- `POST /plan` returns a complete Mission Briefing.
- Frontend can render it without special parsing.

### Task 11: Frontend Plan Wiring

Goal: Connect Objective Input and Mission Briefing UI to the backend.

Implementation:

- Add API client utilities if needed.
- Make Generate Plan call `POST /plan`.
- Render returned Mission Briefing.
- Append reasoning log entries.
- Render returned routes on MapLibre.
- Keep hardcoded data as a fallback while backend is offline.

Verification:

- Start backend and frontend locally.
- Click Generate Plan.
- Confirm briefing and routes update in browser.

### Task 12: WebSocket Live State

Goal: Broadcast operational state from backend to frontend.

Implementation:

- Add FastAPI WebSocket endpoint, likely `/ws/ops`.
- Broadcast state snapshots after planning and after disruption events.
- Throttle frequent updates to roughly 100ms if animation is added.
- Update `frontend-react/src/hooks/useWebSocket.js`.
- Map live convoys, requests, hazards, and route state in `MapView.jsx`.

Verification:

- Connect frontend.
- Trigger a backend state update.
- Confirm frontend receives and renders it without refresh.

### Task 13: Event Injector

Goal: Deterministically simulate one live disruption for the demo.

Implementation:

- Update `backend-python/app/services/event_injector.py`.
- Add endpoint like `POST /events/bridge-collapse`.
- Pick a stable route edge or named demo hazard such as Bridge 7.
- Mutate the graph/state by marking relevant edge IDs blocked/hazardous.
- Broadcast hazard update over WebSocket.

Verification:

- Trigger endpoint.
- Confirm state contains a collapse or blocked-road hazard.
- Confirm map displays hazard.

### Task 14: Autonomous Disruption Replanning

Goal: The event injector must trigger replanning without another coordinator prompt.

Implementation:

- On event injection, call disruption replanning.
- Use prior plan and changed condition as LLM input.
- Compute new routes using the updated graph/hazard state.
- Generate updated Mission Briefing.
- Broadcast updated state, routes, briefing, and reasoning log.

Verification:

- Run objective to generate initial plan.
- Trigger disruption endpoint.
- Confirm updated briefing appears without re-clicking Generate Plan.
- Confirm routes change if the blocked edge affected the prior plan.

### Task 15: Integration Test Full Loop

Goal: Prove the required MVP loop.

Test script:

1. Start backend.
2. Start frontend.
3. Load dashboard.
4. Click Generate Plan with seeded objective.
5. Confirm briefing appears.
6. Confirm routes render.
7. Trigger disruption.
8. Confirm updated briefing and route render without new prompt.

Minimum acceptance:

- No uncaught frontend error.
- Backend health is online.
- Plan endpoint returns valid schemas.
- WebSocket receives state.
- Disruption endpoint causes an updated briefing.

## Phase 2: Do Not Start Without Approval

Stop and ask before starting Phase 2.

Phase 2 candidates:

- Real weather enrichment from Open-Meteo.
- ReliefWeb or GDACS startup context.
- Conversational operational query endpoint/UI.
- More event types: flood, new urgent request, convoy breakdown.
- Route animation and briefing transition polish.

Do not let Layer B live data become required for the demo path.

## Recommended Local Dev Commands

### Backend

From repo root:

```powershell
backend-python\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend-python --reload --port 8000
```

Health URL:

```text
http://127.0.0.1:8000/health
```

### Frontend

From `frontend-react/`:

```powershell
npm install
npm run dev
```

Expected local URL:

```text
http://localhost:5173
```

If `vite` is not recognized, run `npm install` again inside `frontend-react/`.

### Engine

From repo root, after graph exists:

```powershell
$env:PYTHONPATH=(Resolve-Path 'engine-service').Path
engine-service\.venv\Scripts\python.exe -c "from src.graph_loader import load_graph; graph = load_graph(); print(len(graph.nodes), len(graph.edges))"
```

Route smoke test:

```powershell
$env:PYTHONPATH=(Resolve-Path 'engine-service').Path
engine-service\.venv\Scripts\python.exe -c "from src.router import route_between_points; route = route_between_points(51.5014, -0.1419, 51.5079, -0.1280); print(route.to_dict())"
```

## Demo Region

Use Central London for the MVP. Keep the bounding box compact so routing stays fast and the map looks operationally credible.

Current fetch script bbox:

```text
west=-0.1515
south=51.5000
east=-0.1015
north=51.5235
```

This includes areas around Westminster, Trafalgar Square, and the River Thames.

## Operational Seed Data Guidance

Use realistic but fictionalized operational entities:

- Convoy 1: evacuation support near Westminster.
- Convoy 2: medical delivery near Trafalgar Square.
- Convoy 3: supply distribution near Waterloo or Embankment.
- Request: Elm Street shelter evacuation, high priority.
- Request: Sector 4 medical supplies, high priority.
- Request: water and blankets to a lower-priority reception point.
- Hazard: flood-prone road segment near the river.
- Demo disruption: bridge/road collapse that forces a re-route.

Keep IDs stable:

```text
convoy-1
convoy-2
convoy-3
req-med-sector-4
req-evac-elm-shelter
haz-bridge-7-collapse
```

## Mission Briefing Quality Bar

The briefing must be concise, operational, and structured. It should never sound like a chatbot monologue.

Every initial plan and every replan must include:

- Current crisis assessment.
- Highest-risk areas ranked or clearly ordered.
- Recommended convoy/team assignments.
- Predicted bottlenecks.
- Confidence level.
- Backup plan.

For disruption replanning, the updated briefing must explicitly explain:

- What changed.
- Which convoy or route was affected.
- Why the new assignment or route is safer or more feasible.
- Trade-off, such as added travel time or delayed lower-priority request.

## Risk Controls

LLM latency or failure:

- Cache last valid plan and briefing.
- Fall back to deterministic assignment and templated briefing.
- Never freeze the UI during demo.

OSM graph performance:

- Keep demo region compact.
- Load graph once at startup or via cached singleton.

External APIs:

- Only Phase 2.
- Never block the live demo path on weather, ReliefWeb, or GDACS.

Schema mismatch:

- Implement Pydantic schemas before endpoint wiring.
- Validate every response crossing backend/frontend/engine boundaries.

Tone drift:

- Search for forbidden terms before submission:

```powershell
rg -i "game|gameplay|player|score|win condition|level" .
```

Replace any accidental game framing with operational language.

## Submission Checklist

Before Devpost submission:

- Confirm built substantially during July 13-21, 2026.
- Confirm Codex was used as the build tool.
- Confirm GPT-5.6 API or documented fallback model is used in-app.
- Submit under Work and productivity.
- Public repo with runnable README.
- README includes OSM graph regeneration instructions.
- Demo video shows objective -> plan -> briefing -> route execution -> disruption -> autonomous replan -> updated briefing.
- Re-check official Devpost rules/submission form directly before final submission.
