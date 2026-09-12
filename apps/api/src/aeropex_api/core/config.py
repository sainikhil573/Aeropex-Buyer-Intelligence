"""Centralized environment-based configuration."""

from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Aeropex Buyer Intelligence API"
    app_version: str = "0.1.0"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str | None = None
    redis_url: str | None = None
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    enable_docs: bool = True
    cors_allowed_origins: str = "http://localhost:3000"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url or "redis://localhost:6379/0"

    @property
    def resolved_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url or "redis://localhost:6379/0"

    @property
    def resolved_cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
