from __future__ import annotations

import json
from datetime import UTC

import pytest
from aeropex_api.core.config import Settings
from aeropex_api.db.base import Base, import_models
from aeropex_api.db.models import ErrorEvent, Product, Source, SourceObservation
from aeropex_api.db.session import get_db_session
from aeropex_api.main import create_app
from aeropex_api.services.configuration import ProductService, SourceService
from aeropex_api.services.extraction import ExtractionService
from aeropex_api.services.run_lifecycle import utc_now
from aeropex_contracts.enums import (
    ConnectorStatus,
    ExtractionStatus,
    SourceAccessMethod,
    SourceApprovalStatus,
    SourceOperationalStatus,
)
from aeropex_contracts.models import ConnectorResult, ProductCreate, SourceCreate
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
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


def make_product(
    session: Session,
    product_id: str = "PRD-RED-CHILLI",
    name: str = "Red Chilli",
    *,
    aliases: list[str] | None = None,
    variants: list[str] | None = None,
) -> Product:
    return ProductService(session).create_product(
        ProductCreate(
            product_id=product_id,
            category="Spices",
            name=name,
            aliases=aliases or [],
            variants=variants or [],
        )
    )


def make_source(session: Session, source_id: str = "SRC-FIXTURE") -> Source:
    source = SourceService(session).create_source(
        SourceCreate(
            source_id=source_id,
            name="Fixture Source",
            domain="example.com",
            source_type="controlled_fixture",
            access_method=SourceAccessMethod.HTTP,
            operational_status=SourceOperationalStatus.ACTIVE,
        )
    )
    source.approval_status = SourceApprovalStatus.APPROVED
    session.commit()
    session.refresh(source)
    return source


def connector_result(raw_content: str, *, content_type: str | None = "application/json") -> ConnectorResult:
    return ConnectorResult(
        request_id="REQ-EXTRACT",
        run_id="RUN-EXTRACT",
        source_id="SRC-FIXTURE",
        target_url="https://example.com/record",
        status=ConnectorStatus.SUCCESS,
        http_status_code=200,
        content_type=content_type,
        retrieved_at=utc_now(),
        duration_ms=7,
        attempt_count=1,
        raw_content=raw_content,
    )


def complete_payload(**overrides: object) -> str:
    payload = {
        "company_name": "ABC Foods LLC",
        "country": "AE",
        "product": "Red Chilli",
        "requirement": "Seeking dried red chilli flakes.",
        "quantity": "12.5",
        "unit": "MT",
        "specifications": {"packaging": "25kg bags"},
        "contact": {"name": "A Buyer", "email": "BUYER@EXAMPLE.COM", "phone": "+971500000000"},
        "posted_at": "2026-09-12T09:30:00Z",
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_successful_deterministic_extraction_persists_observation(session: Session) -> None:
    make_source(session)
    make_product(session)

    observation = ExtractionService(session).extract_from_connector_result(
        connector_result(complete_payload())
    )

    assert observation is not None
    assert observation.extraction_status == ExtractionStatus.SUCCESS
    assert observation.source_id == "SRC-FIXTURE"
    assert observation.run_id == "RUN-EXTRACT"
    assert observation.source_url == "https://example.com/record"
    assert observation.company_name == "ABC Foods LLC"
    assert observation.product_id == "PRD-RED-CHILLI"
    assert observation.quantity == 12.5
    assert observation.unit == "MT"
    assert observation.contact_email == "buyer@example.com"
    assert observation.posted_at is not None and observation.posted_at.tzinfo == UTC
    assert observation.raw_text == complete_payload()
    assert observation.buyer_id is None
    assert observation.requirement_id is None
    assert session.query(SourceObservation).count() == 1
    assert "buyers" not in Base.metadata.tables
    assert "buyer_requirements" not in Base.metadata.tables


def test_partial_extraction_and_missing_fields_remain_null(session: Session) -> None:
    make_source(session)
    make_product(session)
    payload = json.dumps({"company_name": "Partial Importers", "product": "Red Chilli"})

    observation = ExtractionService(session).extract_from_connector_result(connector_result(payload))

    assert observation is not None
    assert observation.extraction_status == ExtractionStatus.PARTIAL
    assert observation.company_name == "Partial Importers"
    assert observation.requirement_text is None
    assert observation.quantity is None
    assert observation.contact_email is None


def test_no_fabricated_values_for_unknown_product_or_country(session: Session) -> None:
    make_source(session)
    make_product(session)

    observation = ExtractionService(session).extract_from_connector_result(
        connector_result(json.dumps({"company_name": "Unknown Goods", "product": "Saffron"}))
    )

    assert observation is not None
    assert observation.product_id is None
    assert observation.country is None


def test_product_match_by_alias(session: Session) -> None:
    make_source(session)
    make_product(session, aliases=["chilli flakes"])

    alias_observation = ExtractionService(session).extract_from_connector_result(
        connector_result(complete_payload(product="chilli flakes"))
    )

    assert alias_observation is not None
    assert alias_observation.product_id == "PRD-RED-CHILLI"


def test_ambiguous_product_match_left_null(session: Session) -> None:
    make_source(session)
    make_product(session, aliases=["chilli"])
    make_product(session, product_id="PRD-CHILLI-POWDER", name="Chilli Powder", aliases=["chilli"])

    observation = ExtractionService(session).extract_from_connector_result(
        connector_result(complete_payload(product="chilli"))
    )

    assert observation is not None
    assert observation.product_id is None


def test_unsupported_content_is_unstructured_without_error_event(session: Session) -> None:
    make_source(session)

    observation = ExtractionService(session).extract_from_connector_result(
        connector_result("buyer-looking text", content_type="text/plain")
    )

    assert observation is not None
    assert observation.extraction_status == ExtractionStatus.UNSTRUCTURED
    assert observation.company_name is None
    assert session.query(ErrorEvent).count() == 0


def test_malformed_payload_persists_failed_observation_and_error_event(session: Session) -> None:
    make_source(session)

    observation = ExtractionService(session).extract_from_connector_result(connector_result("{bad-json"))

    assert observation is not None
    assert observation.extraction_status == ExtractionStatus.FAILED
    assert observation.raw_text == "{bad-json"
    event = session.query(ErrorEvent).one()
    assert event.error_type == "extractor_invalid_payload"


def test_failed_connector_result_does_not_create_observation(session: Session) -> None:
    make_source(session)
    result = ConnectorResult(
        request_id="REQ-FAILED",
        run_id="RUN-FAILED",
        source_id="SRC-FIXTURE",
        target_url="https://example.com/record",
        status=ConnectorStatus.FAILED,
        retrieved_at=utc_now(),
        duration_ms=0,
        attempt_count=1,
        raw_content=None,
        error_type="connector_http_error",
        error_message="failed",
    )

    observation = ExtractionService(session).extract_from_connector_result(result)

    assert observation is None
    assert session.query(SourceObservation).count() == 0


def test_observation_persistence_failure_rolls_back_before_error_event(
    session: Session,
) -> None:
    make_source(session)
    make_product(session)
    session.execute(text("DROP TABLE source_observations"))
    session.commit()

    with pytest.raises(OperationalError):
        ExtractionService(session).extract_from_connector_result(connector_result(complete_payload()))

    events = session.query(ErrorEvent).all()
    assert len(events) == 1
    assert events[0].error_type == "observation_persistence_error"


def test_observation_api_list_read_filters_and_pagination(session: Session) -> None:
    make_source(session)
    make_product(session)
    service = ExtractionService(session)
    first = service.extract_from_connector_result(connector_result(complete_payload()))
    service.extract_from_connector_result(connector_result(json.dumps({"company_name": "Only Company"})))
    app = create_app(Settings())

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    listed = client.get(
        "/api/v1/observations",
        params={"limit": 1, "offset": 0, "source_id": "SRC-FIXTURE", "product_id": "PRD-RED-CHILLI"},
    )
    by_id = client.get(f"/api/v1/observations/{first.observation_id}")
    missing = client.get("/api/v1/observations/OBS-MISSING")

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["product_id"] == "PRD-RED-CHILLI"
    assert by_id.status_code == 200
    assert by_id.json()["observation_id"] == first.observation_id
    assert by_id.json()["buyer_id"] is None
    assert by_id.json()["requirement_id"] is None
    assert missing.status_code == 404


def test_controlled_extraction_test_endpoint_creates_observation(session: Session) -> None:
    make_source(session)
    make_product(session)
    app = create_app(Settings())

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    response = client.post(
        "/api/v1/extractions/test",
        json={"source_id": "SRC-FIXTURE", "raw_content": complete_payload()},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["extraction_status"] == "success"
    assert body["product_id"] == "PRD-RED-CHILLI"
    assert body["buyer_id"] is None
