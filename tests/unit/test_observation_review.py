from __future__ import annotations

import json

import pytest
from aeropex_api.core.config import Settings
from aeropex_api.db.base import Base, import_models
from aeropex_api.db.models import AuditEvent, ObservationReview, Source, SourceObservation
from aeropex_api.db.session import get_db_session
from aeropex_api.main import create_app
from aeropex_api.services.configuration import ProductService, SourceService
from aeropex_api.services.extraction import ExtractionService
from aeropex_api.services.observation_review import ObservationReviewService
from aeropex_api.services.run_lifecycle import utc_now
from aeropex_contracts.enums import (
    ConnectorStatus,
    ObservationReviewStatus,
    SourceAccessMethod,
    SourceApprovalStatus,
    SourceOperationalStatus,
)
from aeropex_contracts.models import ConnectorResult, ProductCreate, SourceCreate
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
    app = create_app(Settings())

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app)


def make_observation(session: Session) -> SourceObservation:
    SourceService(session).create_source(
        SourceCreate(
            source_id="SRC-FIXTURE",
            name="Fixture Source",
            domain="example.com",
            source_type="controlled_fixture",
            access_method=SourceAccessMethod.HTTP,
            operational_status=SourceOperationalStatus.ACTIVE,
        )
    )
    source = session.get(Source, "SRC-FIXTURE")
    assert source is not None
    source.approval_status = SourceApprovalStatus.APPROVED
    ProductService(session).create_product(
        ProductCreate(product_id="PRD-RED-CHILLI", category="Spices", name="Red Chilli")
    )
    session.commit()
    observation = ExtractionService(session).extract_from_connector_result(
        ConnectorResult(
            request_id="REQ-REVIEW",
            run_id="RUN-REVIEW",
            source_id="SRC-FIXTURE",
            target_url="https://example.com/record",
            status=ConnectorStatus.SUCCESS,
            http_status_code=200,
            content_type="application/json",
            retrieved_at=utc_now(),
            duration_ms=1,
            attempt_count=1,
            raw_content=json.dumps(
                {
                    "company_name": "Example Foods LLC",
                    "country": "AE",
                    "product": "Red Chilli",
                    "requirement": "Seeking dried red chilli flakes.",
                    "quantity": "10",
                    "unit": "MT",
                    "contact": {"email": "buyer@example.com"},
                }
            ),
        )
    )
    assert observation is not None
    return observation


def test_default_review_state_is_unreviewed(client: TestClient, session: Session) -> None:
    observation = make_observation(session)

    response = client.get(f"/api/v1/observations/{observation.observation_id}/review")

    assert response.status_code == 200
    assert response.json()["status"] == "unreviewed"
    assert response.json()["review_id"] is None


@pytest.mark.parametrize("review_status", ["accepted", "rejected", "needs_review", "unreviewed"])
def test_review_status_and_notes_update(
    client: TestClient,
    session: Session,
    review_status: str,
) -> None:
    observation = make_observation(session)

    response = client.patch(
        f"/api/v1/observations/{observation.observation_id}/review",
        json={"status": review_status, "review_notes": " Keep for review. "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == review_status
    assert body["review_notes"] == "Keep for review."
    assert body["reviewed_by"] == "local-admin"
    assert session.query(ObservationReview).count() == 1


def test_review_change_preserves_observation_and_creates_audit_event(
    client: TestClient,
    session: Session,
) -> None:
    observation = make_observation(session)
    original_raw_text = observation.raw_text

    first = client.patch(
        f"/api/v1/observations/{observation.observation_id}/review",
        json={"status": "needs_review", "review_notes": "Need contact check."},
    )
    second = client.patch(
        f"/api/v1/observations/{observation.observation_id}/review",
        json={"status": "accepted", "review_notes": "Useful candidate opportunity."},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    session.refresh(observation)
    assert observation.raw_text == original_raw_text
    assert observation.buyer_id is None
    assert observation.requirement_id is None
    assert session.query(ObservationReview).count() == 1
    events = (
        session.query(AuditEvent)
        .filter(AuditEvent.action == "observation_review_updated")
        .order_by(AuditEvent.timestamp)
        .all()
    )
    assert len(events) == 2
    assert events[0].action == "observation_review_updated"
    assert events[0].before_state["status"] == "unreviewed"
    assert events[0].after_state["status"] == "needs_review"
    assert events[1].before_state["status"] == "needs_review"
    assert events[1].after_state["status"] == "accepted"


def test_review_api_rejects_invalid_status_and_missing_observation(client: TestClient) -> None:
    invalid = client.patch(
        "/api/v1/observations/OBS-MISSING/review",
        json={"status": "verified", "review_notes": "bad"},
    )
    missing = client.patch(
        "/api/v1/observations/OBS-MISSING/review",
        json={"status": "accepted", "review_notes": "missing"},
    )

    assert invalid.status_code == 422
    assert missing.status_code == 404


def test_observation_list_includes_review_state_filtering_and_pagination(
    client: TestClient,
    session: Session,
) -> None:
    first = make_observation(session)
    second = ExtractionService(session).extract_from_connector_result(
        ConnectorResult(
            request_id="REQ-SECOND",
            run_id="RUN-REVIEW",
            source_id="SRC-FIXTURE",
            target_url="https://example.com/second",
            status=ConnectorStatus.SUCCESS,
            http_status_code=200,
            content_type="application/json",
            retrieved_at=utc_now(),
            duration_ms=1,
            attempt_count=1,
            raw_content=json.dumps({"company_name": "Second Foods LLC"}),
        )
    )
    assert second is not None
    ObservationReviewService(session).update_review(
        first.observation_id,
        status=ObservationReviewStatus.ACCEPTED,
        review_notes="Accepted for next stage.",
    )

    accepted = client.get("/api/v1/observations", params={"review_status": "accepted", "limit": 1})
    unreviewed = client.get("/api/v1/observations", params={"review_status": "unreviewed"})

    assert accepted.status_code == 200
    assert len(accepted.json()) == 1
    assert accepted.json()[0]["review_status"] == "accepted"
    assert unreviewed.status_code == 200
    assert [row["observation_id"] for row in unreviewed.json()] == [second.observation_id]


def test_review_counts_include_missing_review_rows(session: Session) -> None:
    observation = make_observation(session)
    counts = ObservationReviewService(session).review_counts()
    assert counts["unreviewed"] == 1

    ObservationReviewService(session).update_review(
        observation.observation_id,
        status=ObservationReviewStatus.REJECTED,
        review_notes=None,
    )

    counts = ObservationReviewService(session).review_counts()
    assert counts["unreviewed"] == 0
    assert counts["rejected"] == 1
