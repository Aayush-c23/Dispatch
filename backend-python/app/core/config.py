import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Resolve and load .env files explicitly from both root and backend directories
backend_dir_env = Path(__file__).resolve().parents[2] / ".env"
workspace_root_env = Path(__file__).resolve().parents[3] / ".env"

if backend_dir_env.exists():
    load_dotenv(dotenv_path=backend_dir_env, override=True)
if workspace_root_env.exists():
    load_dotenv(dotenv_path=workspace_root_env, override=True)

# ── Guard against placeholder values ────────────────────────
_PLACEHOLDERS = {"your_openai_api_key_here", "your_groq_api_key_here", "", "None"}


def _clean_key(env_var: str) -> str | None:
    value = os.getenv(env_var)
    return None if value in _PLACEHOLDERS else value


class Settings(BaseSettings):
    app_name: str = "ReliefGrid AI Orchestration API"
    app_version: str = "0.1.0"
    environment: str = "local"

    # ── LLM provider toggle ("openai" | "groq") ─────────────
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()

    # ── OpenAI credentials ──────────────────────────────────
    openai_api_key: str | None = _clean_key("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # ── Groq credentials ────────────────────────────────────
    groq_api_key: str | None = _clean_key("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # ── CORS ─────────────────────────────────────────────────
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Computed helpers ─────────────────────────────────────
    @property
    def active_llm_api_key(self) -> str | None:
        """Return the API key for the currently selected provider."""
        if self.llm_provider == "groq":
            return self.groq_api_key
        return self.openai_api_key

    @property
    def active_llm_model(self) -> str:
        """Return the model name for the currently selected provider."""
        if self.llm_provider == "groq":
            return self.groq_model
        return self.openai_model

    @property
    def active_llm_base_url(self) -> str | None:
        """Return the base URL override (Groq uses an OpenAI-compatible endpoint)."""
        if self.llm_provider == "groq":
            return "https://api.groq.com/openai/v1"
        return None


settings = Settings()
