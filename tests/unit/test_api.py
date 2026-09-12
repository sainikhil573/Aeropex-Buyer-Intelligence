from aeropex_api.core.config import Settings
from aeropex_api.main import create_app
from fastapi.testclient import TestClient


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "aeropex-api"}


def test_basic_application_startup() -> None:
    app = create_app()

    assert app.title == "Aeropex Buyer Intelligence API"


def test_readiness_endpoint_is_structured_for_dependency_checks() -> None:
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "postgresql" in body["checks"]
    assert "redis" in body["checks"]


def test_cors_uses_configured_local_origins() -> None:
    client = TestClient(create_app(Settings(cors_allowed_origins="http://localhost:3000")))

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
