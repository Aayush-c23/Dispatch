"""Application settings for the ReliefGrid AI orchestration backend."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ReliefGrid AI Orchestration API"
    app_version: str = "0.1.0"
    environment: str = "local"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6"
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
