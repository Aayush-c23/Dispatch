"""FastAPI entrypoint for the ReliefGrid AI orchestration backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

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
