"""Application factory for the Aeropex API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from aeropex_api.api.v1.router import api_router
from aeropex_api.core.config import Settings, get_settings
from aeropex_api.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application-level lifecycle hook for future dependency setup."""

    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        docs_url="/docs" if app_settings.enable_docs else None,
        redoc_url="/redoc" if app_settings.enable_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "aeropex-api"}

    @app.get("/ready", tags=["system"])
    async def ready() -> dict[str, object]:
        checks = {
            "postgresql": {"status": "not_configured"},
            "redis": {"status": "not_configured"},
        }
        if app_settings.database_url:
            checks["postgresql"] = {"status": "configured"}
        if app_settings.redis_url:
            checks["redis"] = {"status": "configured"}
        return {"status": "ready", "service": "aeropex-api", "checks": checks}

    return app


app = create_app()
