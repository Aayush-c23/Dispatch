"""Phase 1 FastAPI entrypoint placeholder for ReliefGrid AI."""
from fastapi import FastAPI

app = FastAPI(title="ReliefGrid AI Orchestration API")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "placeholder", "phase": "0"}
