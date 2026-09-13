import pytest
from aeropex_api.db.base import Base, import_models
from aeropex_api.db.models import AuditEvent
from aeropex_api.db.session import get_db_session
from aeropex_api.main import create_app
from aeropex_api.services.bootstrap import bootstrap_configuration
from aeropex_api.services.configuration import (
    DuplicateConfigurationError,
    InvalidConfigurationTransition,
    ProductService,
    SourceService,
)
from aeropex_contracts.enums import (
    SourceAccessMethod,
    SourceApprovalStatus,
    SourceOperationalStatus,
)
from aeropex_contracts.models import ProductCreate, ProductUpdate, SourceCreate, SourceUpdate
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def session() -> Session:
    import_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as db_session:
        yield db_session


@pytest.fixture()
def client(session: Session) -> TestClient:
    app = create_app()

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app)


def test_product_creation_normalizes_and_audits(session: Session) -> None:
    product = ProductService(session).create_product(
        ProductCreate(
            product_id=" PRD-TEST ",
            category=" Spices ",
            name=" Test Spice ",
            aliases=[" Alias ", " "],
            variants=[],
            hs_codes=[],
        )
    )

    assert product.product_id == "PRD-TEST"
    assert product.name == "Test Spice"
    assert product.aliases == ["Alias"]
    event = session.query(AuditEvent).filter_by(entity_type="product", entity_id="PRD-TEST").one()
    assert event.action == "product_created"


def test_product_duplicate_id_and_active_name_are_rejected(session: Session) -> None:
    service = ProductService(session)
    service.create_product(ProductCreate(product_id="PRD-1", category="Spices", name="Cumin"))

    with pytest.raises(DuplicateConfigurationError):
        service.create_product(ProductCreate(product_id="PRD-1", category="Spices", name="Other"))

    with pytest.raises(DuplicateConfigurationError):
        service.create_product(ProductCreate(product_id="PRD-2", category="Spices", name="Cumin"))


def test_product_update_and_deactivation_audit(session: Session) -> None:
    service = ProductService(session)
    service.create_product(ProductCreate(product_id="PRD-UPDATE", category="Spices", name="Pepper"))

    product = service.update_product("PRD-UPDATE", ProductUpdate(active=False, variants=["Fine"]))

    assert product.active is False
    assert product.variants == ["Fine"]
    actions = [event.action for event in session.query(AuditEvent).filter_by(entity_id="PRD-UPDATE").all()]
    assert "product_deactivated" in actions


def test_source_creation_defaults_to_candidate_and_audits(session: Session) -> None:
    source = SourceService(session).create_source(
        SourceCreate(
            source_id="SRC-1",
            name=" Example Source ",
            source_type="directory",
            access_method=SourceAccessMethod.HTTP,
        )
    )

    assert source.approval_status == SourceApprovalStatus.CANDIDATE
    assert source.operational_status == SourceOperationalStatus.ACTIVE
    assert session.query(AuditEvent).filter_by(entity_type="source", entity_id="SRC-1").count() == 1


def test_source_approval_rejection_and_invalid_transition(session: Session) -> None:
    service = SourceService(session)
    service.create_source(SourceCreate(source_id="SRC-APPROVE", name="Candidate", source_type="directory", access_method="http"))

    approved = service.approve_source("SRC-APPROVE")

    assert approved.approval_status == SourceApprovalStatus.APPROVED
    with pytest.raises(InvalidConfigurationTransition):
        service.reject_source("SRC-APPROVE")


def test_eligible_source_filtering(session: Session) -> None:
    service = SourceService(session)
    service.create_source(SourceCreate(source_id="SRC-ELIGIBLE", name="Eligible", source_type="directory", access_method="http"))
    service.approve_source("SRC-ELIGIBLE")
    service.create_source(
        SourceCreate(
            source_id="SRC-DISABLED",
            name="Disabled",
            source_type="directory",
            access_method="http",
            operational_status=SourceOperationalStatus.DISABLED,
        )
    )
    service.approve_source("SRC-DISABLED")

    assert [source.source_id for source in service.list_eligible_sources(limit=10, offset=0)] == ["SRC-ELIGIBLE"]


def test_source_operational_update_audits(session: Session) -> None:
    service = SourceService(session)
    service.create_source(SourceCreate(source_id="SRC-OPS", name="Ops", source_type="directory", access_method="http"))

    source = service.update_source("SRC-OPS", SourceUpdate(operational_status=SourceOperationalStatus.DEGRADED))

    assert source.operational_status == SourceOperationalStatus.DEGRADED
    assert (
        session.query(AuditEvent)
        .filter_by(entity_type="source", entity_id="SRC-OPS", action="source_operational_status_changed")
        .count()
        == 1
    )


def test_configuration_bootstrap_is_idempotent(session: Session) -> None:
    bootstrap_configuration(session)
    bootstrap_configuration(session)

    assert len(ProductService(session).list_products(limit=100, offset=0)) == 6
    assert len(SourceService(session).list_sources(limit=100, offset=0)) == 3


def test_product_api_crud_lite_and_404(client: TestClient) -> None:
    created = client.post(
        "/api/v1/products",
        json={"product_id": "PRD-API", "category": "Spices", "name": "API Spice"},
    )

    assert created.status_code == 201
    assert client.get("/api/v1/products/PRD-API").json()["name"] == "API Spice"
    patched = client.patch("/api/v1/products/PRD-API", json={"active": False})
    assert patched.status_code == 200
    assert patched.json()["active"] is False
    assert client.get("/api/v1/products/PRD-MISSING").status_code == 404


def test_product_api_duplicate_returns_409(client: TestClient) -> None:
    payload = {"product_id": "PRD-DUP", "category": "Spices", "name": "Duplicate"}
    assert client.post("/api/v1/products", json=payload).status_code == 201

    response = client.post("/api/v1/products", json=payload)

    assert response.status_code == 409


def test_source_api_workflow_and_eligible(client: TestClient) -> None:
    created = client.post(
        "/api/v1/sources",
        json={"source_id": "SRC-API", "name": "API Source", "source_type": "directory", "access_method": "http"},
    )

    assert created.status_code == 201
    assert created.json()["approval_status"] == "candidate"
    approved = client.post("/api/v1/sources/SRC-API/approve")
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"
    eligible = client.get("/api/v1/sources/eligible")
    assert [source["source_id"] for source in eligible.json()] == ["SRC-API"]


def test_source_api_reject_and_invalid_transition(client: TestClient) -> None:
    client.post(
        "/api/v1/sources",
        json={"source_id": "SRC-REJECT", "name": "Rejectable", "source_type": "directory", "access_method": "manual"},
    )
    assert client.post("/api/v1/sources/SRC-REJECT/reject").status_code == 200

    response = client.post("/api/v1/sources/SRC-REJECT/approve")

    assert response.status_code == 400


def test_source_api_patch_and_404(client: TestClient) -> None:
    client.post(
        "/api/v1/sources",
        json={"source_id": "SRC-PATCH", "name": "Patchable", "source_type": "directory", "access_method": "http"},
    )

    patched = client.patch("/api/v1/sources/SRC-PATCH", json={"operational_status": "disabled"})

    assert patched.status_code == 200
    assert patched.json()["operational_status"] == "disabled"
    assert client.get("/api/v1/sources/SRC-MISSING").status_code == 404
