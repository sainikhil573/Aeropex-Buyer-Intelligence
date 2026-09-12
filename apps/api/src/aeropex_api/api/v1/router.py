"""API v1 router."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
async def versioned_health() -> dict[str, str]:
    return {"status": "healthy", "service": "aeropex-api", "api_version": "v1"}
