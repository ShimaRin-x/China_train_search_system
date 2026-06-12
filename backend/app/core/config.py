from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "China Railway Route Visualization"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://railway:railway@postgres:5432/railway_viz"
    redis_url: str = "redis://redis:6379/0"
    backend_cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
