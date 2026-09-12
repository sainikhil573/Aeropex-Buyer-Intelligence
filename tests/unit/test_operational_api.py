import pytest
from aeropex_api.api.v1.router import api_router
from aeropex_api.db.base import Base, import_models
from aeropex_api.db.session import get_db_session
from aeropex_api.main import create_app
from aeropex_api.services.bootstrap import BUYER_DISCOVERY_AGENT_ID, bootstrap_initial_agents
from aeropex_api.services.run_lifecycle import AgentRunService
from aeropex_contracts.enums import TriggerType
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def api_session() -> Session:
    import_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        bootstrap_initial_agents(session)
        yield session


@pytest.fixture()
def client(api_session: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from aeropex_workers import celery_app as worker_module

    app = create_app()

    def override_session():
        yield api_session

    app.dependency_overrides[get_db_session] = override_session
    session_factory = sessionmaker(bind=api_session.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr(worker_module, "create_session_factory", lambda: session_factory)
    monkeypatch.setattr("aeropex_api.api.v1.router.operational_test_run_task", worker_module.operational_test_run_task)
    worker_module.celery_app.conf.task_always_eager = True
    worker_module.celery_app.conf.task_eager_propagates = False
    return TestClient(app)


def test_router_is_api_v1_router() -> None:
    assert api_router.prefix == ""


def test_agent_listing_api(client: TestClient) -> None:
    response = client.get("/api/v1/agents")

    assert response.status_code == 200
    assert response.json()[0]["agent_id"] == BUYER_DISCOVERY_AGENT_ID


def test_agent_detail_api(client: TestClient) -> None:
    response = client.get(f"/api/v1/agents/{BUYER_DISCOVERY_AGENT_ID}")

    assert response.status_code == 200
    assert response.json()["name"] == "Buyer Discovery"


def test_missing_agent_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/agents/AGT-MISSING")

    assert response.status_code == 404


def test_run_listing_and_pagination(client: TestClient, api_session: Session) -> None:
    service = AgentRunService(api_session)
    for index in range(3):
        service.create_run(
            agent_id=BUYER_DISCOVERY_AGENT_ID,
            trigger_type=TriggerType.MANUAL,
            run_id=f"RUN-PAGE-{index}",
        )

    response = client.get("/api/v1/runs?limit=2&offset=1")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_run_detail_api(client: TestClient, api_session: Session) -> None:
    run = AgentRunService(api_session).create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)

    response = client.get(f"/api/v1/runs/{run.run_id}")

    assert response.status_code == 200
    assert response.json()["run_id"] == run.run_id


def test_missing_run_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/runs/RUN-MISSING")

    assert response.status_code == 404


def test_run_creation_api_queues_safe_operational_task(client: TestClient) -> None:
    response = client.post("/api/v1/runs", json={"agent_id": BUYER_DISCOVERY_AGENT_ID})

    assert response.status_code == 202
    body = response.json()
    assert body["agent_id"] == BUYER_DISCOVERY_AGENT_ID
    assert body["status"] == "queued"
    assert body["task_id"] is not None


def test_run_creation_missing_agent_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/runs", json={"agent_id": "AGT-MISSING"})

    assert response.status_code == 404
