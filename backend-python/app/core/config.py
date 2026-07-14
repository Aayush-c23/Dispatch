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

# Guard against placeholder values
api_key = os.getenv("OPENAI_API_KEY")
if api_key in {"your_openai_api_key_here", "", "None"}:
    api_key = None


class Settings(BaseSettings):
    app_name: str = "ReliefGrid AI Orchestration API"
    app_version: str = "0.1.0"
    environment: str = "local"
    openai_api_key: str | None = api_key
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6")
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
