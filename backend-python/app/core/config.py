from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6"
settings = Settings()
