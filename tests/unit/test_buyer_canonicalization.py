from __future__ import annotations

import json
from datetime import datetime

import pytest
from aeropex_api.core.config import Settings
from aeropex_api.db.base import Base, import_models
from aeropex_api.db.models import AuditEvent, Buyer, BuyerRequirement, Source, SourceObservation
from aeropex_api.db.session import get_db_session
from aeropex_api.main import create_app
from aeropex_api.services.buyer_canonicalization import (
    BuyerCanonicalizationService,
    normalize_company_name,
)
from aeropex_api.services.configuration import ProductService, SourceService
from aeropex_api.services.extraction import ExtractionService
from aeropex_api.services.observation_review import ObservationReviewService
from aeropex_api.services.run_lifecycle import utc_now
from aeropex_contracts.enums import (
    BuyerRequirementStatus,
    ConnectorStatus,
    EntityResolutionStatus,
    ObservationReviewStatus,
    SourceAccessMethod,
    SourceApprovalStatus,
    SourceOperationalStatus,
    VerificationStatus,
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
        seed_configuration(db_session)
        yield db_session


@pytest.fixture()
def client(session: Session) -> TestClient:
    app = create_app(Settings())

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app)


def seed_configuration(session: Session) -> None:
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


def make_observation(
    session: Session,
    *,
    company_name: str | None = "Example Foods LLC",
    country: str | None = "United States",
    requirement_text: str | None = "Seeking Red Chilli 1000 kg for import.",
    quantity: float | str | None = "1000",
    unit: str | None = "kg",
    request_id: str = "REQ-CANON",
) -> SourceObservation:
    payload: dict[str, object] = {
        "product": "Red Chilli",
        "specifications": {"grade": "A"},
        "posted_at": "2026-09-13T10:00:00Z",
    }
    if company_name is not None:
        payload["company_name"] = company_name
    if country is not None:
        payload["country"] = country
    if requirement_text is not None:
        payload["requirement"] = requirement_text
    if quantity is not None:
        payload["quantity"] = quantity
    if unit is not None:
        payload["unit"] = unit
    observation = ExtractionService(session).extract_from_connector_result(
        ConnectorResult(
            request_id=request_id,
            run_id="RUN-CANON",
            source_id="SRC-FIXTURE",
            target_url=f"https://example.com/{request_id.lower()}",
            status=ConnectorStatus.SUCCESS,
            http_status_code=200,
            content_type="application/json",
            retrieved_at=utc_now(),
            duration_ms=1,
            attempt_count=1,
            raw_content=json.dumps(payload),
        )
    )
    assert observation is not None
    return observation


def accept(session: Session, observation: SourceObservation) -> None:
    ObservationReviewService(session).update_review(
        observation.observation_id,
        status=ObservationReviewStatus.ACCEPTED,
        review_notes="Accepted for canonicalization.",
    )


def add_buyer(
    session: Session,
    buyer_id: str,
    *,
    company_name: str = "Example Foods LLC",
    country: str | None = "United States",
    primary_domain: str | None = None,
) -> Buyer:
    now = utc_now()
    buyer = Buyer(
        buyer_id=buyer_id,
        company_name=company_name,
        normalized_company_name=normalize_company_name(company_name) or company_name.lower(),
        country=country,
        website=f"https://{primary_domain}" if primary_domain else None,
        primary_domain=primary_domain,
        company_type=None,
        verification_status=VerificationStatus.UNVERIFIED,
        confidence_score=None,
        created_at=now,
        updated_at=now,
    )
    session.add(buyer)
    session.commit()
    return buyer


def test_new_buyer_requirement_linkage_and_evidence_immutability(session: Session) -> None:
    observation = make_observation(session)
    accept(session, observation)
    before = {
        "raw_text": observation.raw_text,
        "source_url": observation.source_url,
        "captured_at": observation.captured_at,
        "company_name": observation.company_name,
        "requirement_text": observation.requirement_text,
    }

    result = BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    assert result.status == EntityResolutionStatus.CREATED
    assert result.buyer_id is not None
    assert result.requirement_id is not None
    buyer = session.get(Buyer, result.buyer_id)
    requirement = session.get(BuyerRequirement, result.requirement_id)
    session.refresh(observation)
    assert buyer is not None
    assert buyer.company_name == "Example Foods LLC"
    assert buyer.normalized_company_name == "example foods"
    assert buyer.verification_status == VerificationStatus.UNVERIFIED
    assert buyer.confidence_score is None
    assert requirement is not None
    assert requirement.buyer_id == buyer.buyer_id
    assert requirement.product_id == "PRD-RED-CHILLI"
    assert requirement.requirement_text == "Seeking Red Chilli 1000 kg for import."
    assert requirement.quantity == 1000
    assert requirement.unit == "kg"
    assert requirement.specifications == {"grade": "A"}
    assert requirement.posted_at is not None
    assert requirement.status == BuyerRequirementStatus.ACTIVE
    assert observation.buyer_id == buyer.buyer_id
    assert observation.requirement_id == requirement.requirement_id
    assert observation.raw_text == before["raw_text"]
    assert observation.source_url == before["source_url"]
    assert observation.captured_at == before["captured_at"]
    assert observation.company_name == before["company_name"]
    assert observation.requirement_text == before["requirement_text"]
    assert {event.action for event in session.query(AuditEvent).all()} >= {
        "buyer_created",
        "buyer_requirement_created",
        "source_observation_linked",
    }


def test_existing_buyer_match_normalizes_legal_suffix_case_and_whitespace(session: Session) -> None:
    existing = add_buyer(session, "BUY-EXISTING", company_name="Example Foods LLC")
    observation = make_observation(
        session,
        company_name="  EXAMPLE   FOODS L.L.C. ",
        request_id="REQ-MATCH",
    )
    accept(session, observation)

    result = BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    assert result.status == EntityResolutionStatus.MATCHED
    assert result.buyer_id == existing.buyer_id
    assert result.matched_existing_buyer is True
    assert session.query(Buyer).count() == 1
    assert session.query(BuyerRequirement).count() == 1


def test_different_country_does_not_auto_match_by_name_only(session: Session) -> None:
    add_buyer(session, "BUY-US", country="United States")
    observation = make_observation(session, country="Canada", request_id="REQ-CA")
    accept(session, observation)

    result = BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    assert result.status == EntityResolutionStatus.CREATED
    assert result.buyer_id != "BUY-US"
    assert session.query(Buyer).count() == 2


def test_multiple_exact_matches_are_ambiguous_and_unlinked(session: Session) -> None:
    add_buyer(session, "BUY-A")
    add_buyer(session, "BUY-B")
    observation = make_observation(session, request_id="REQ-AMBIG")
    accept(session, observation)

    result = BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    assert result.status == EntityResolutionStatus.AMBIGUOUS
    assert result.candidate_buyer_ids == ["BUY-A", "BUY-B"]
    session.refresh(observation)
    assert observation.buyer_id is None
    assert observation.requirement_id is None
    assert session.query(BuyerRequirement).count() == 0


def test_weak_fuzzy_match_does_not_auto_merge(session: Session) -> None:
    add_buyer(session, "BUY-GLOBAL", company_name="Global Foods International", country="United States")
    observation = make_observation(session, company_name="Global Foods", request_id="REQ-FUZZY")
    accept(session, observation)

    result = BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    assert result.status == EntityResolutionStatus.CREATED
    assert result.buyer_id != "BUY-GLOBAL"
    assert session.query(Buyer).count() == 2


def test_missing_company_unaccepted_and_already_canonicalized_results(session: Session) -> None:
    missing_company = make_observation(session, company_name=None, request_id="REQ-NO-COMPANY")
    accept(session, missing_company)
    unaccepted = make_observation(session, request_id="REQ-UNACCEPTED")

    missing_result = BuyerCanonicalizationService(session).canonicalize_observation(
        missing_company.observation_id
    )
    unaccepted_result = BuyerCanonicalizationService(session).canonicalize_observation(unaccepted.observation_id)

    assert missing_result.status == EntityResolutionStatus.INELIGIBLE
    assert unaccepted_result.status == EntityResolutionStatus.INELIGIBLE

    accepted = make_observation(session, request_id="REQ-IDEMPOTENT")
    accept(session, accepted)
    first = BuyerCanonicalizationService(session).canonicalize_observation(accepted.observation_id)
    second = BuyerCanonicalizationService(session).canonicalize_observation(accepted.observation_id)

    assert second.status == EntityResolutionStatus.ALREADY_CANONICALIZED
    assert second.buyer_id == first.buyer_id
    assert second.requirement_id == first.requirement_id
    assert session.query(Buyer).count() == 1
    assert session.query(BuyerRequirement).count() == 1


def test_buyer_can_be_created_without_requirement_when_text_missing(session: Session) -> None:
    observation = make_observation(
        session,
        requirement_text=None,
        quantity=None,
        unit=None,
        request_id="REQ-NO-REQ",
    )
    accept(session, observation)

    result = BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    assert result.status == EntityResolutionStatus.CREATED
    assert result.buyer_id is not None
    assert result.requirement_id is None
    session.refresh(observation)
    assert observation.buyer_id == result.buyer_id
    assert observation.requirement_id is None
    assert session.query(BuyerRequirement).count() == 0


def test_requirement_failure_rolls_back_buyer_creation(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    observation = make_observation(session, request_id="REQ-REQ-FAIL")
    accept(session, observation)

    def fail_requirement(*args: object, **kwargs: object) -> None:
        raise RuntimeError("requirement failure")

    monkeypatch.setattr(BuyerCanonicalizationService, "_create_requirement_if_supported", fail_requirement)

    with pytest.raises(RuntimeError):
        BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    session.refresh(observation)
    assert session.query(Buyer).count() == 0
    assert session.query(BuyerRequirement).count() == 0
    assert observation.buyer_id is None


def test_observation_link_failure_rolls_back_requirement_creation(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observation = make_observation(session, request_id="REQ-LINK-FAIL")
    accept(session, observation)

    def fail_link(*args: object, **kwargs: object) -> None:
        raise RuntimeError("link failure")

    monkeypatch.setattr(BuyerCanonicalizationService, "_link_observation", fail_link)

    with pytest.raises(RuntimeError):
        BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    session.refresh(observation)
    assert session.query(Buyer).count() == 0
    assert session.query(BuyerRequirement).count() == 0
    assert observation.buyer_id is None
    assert observation.requirement_id is None


def test_canonicalization_and_buyer_read_apis(client: TestClient, session: Session) -> None:
    observation = make_observation(session, request_id="REQ-API")
    accept(session, observation)

    created = client.post(f"/api/v1/observations/{observation.observation_id}/canonicalize")
    again = client.post(f"/api/v1/observations/{observation.observation_id}/canonicalize")
    missing = client.post("/api/v1/observations/OBS-MISSING/canonicalize")

    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "created"
    assert body["buyer_id"] is not None
    assert body["requirement_id"] is not None
    assert again.status_code == 200
    assert again.json()["status"] == "already_canonicalized"
    assert missing.status_code == 404

    buyers = client.get("/api/v1/buyers", params={"limit": 10, "offset": 0, "country": "United States"})
    buyer = client.get(f"/api/v1/buyers/{body['buyer_id']}")
    requirements = client.get(f"/api/v1/buyers/{body['buyer_id']}/requirements")
    requirement = client.get(f"/api/v1/requirements/{body['requirement_id']}")

    assert buyers.status_code == 200
    assert buyers.json()[0]["requirements_count"] == 1
    assert buyer.status_code == 200
    assert buyer.json()["verification_status"] == "unverified"
    assert requirements.status_code == 200
    assert requirements.json()[0]["requirement_id"] == body["requirement_id"]
    assert requirement.status_code == 200
    assert requirement.json()["product_id"] == "PRD-RED-CHILLI"


def test_api_ambiguous_and_ineligible_results(client: TestClient, session: Session) -> None:
    add_buyer(session, "BUY-A")
    add_buyer(session, "BUY-B")
    ambiguous = make_observation(session, request_id="REQ-API-AMBIG")
    ineligible = make_observation(session, request_id="REQ-API-INELIGIBLE")
    accept(session, ambiguous)

    ambiguous_response = client.post(f"/api/v1/observations/{ambiguous.observation_id}/canonicalize")
    ineligible_response = client.post(f"/api/v1/observations/{ineligible.observation_id}/canonicalize")

    assert ambiguous_response.status_code == 200
    assert ambiguous_response.json()["status"] == "ambiguous"
    assert ambiguous_response.json()["candidate_buyer_ids"] == ["BUY-A", "BUY-B"]
    assert ineligible_response.status_code == 200
    assert ineligible_response.json()["status"] == "ineligible"


def test_buyer_list_pagination_and_filters(client: TestClient, session: Session) -> None:
    add_buyer(session, "BUY-ONE", company_name="Alpha Foods LLC", country="United States")
    add_buyer(session, "BUY-TWO", company_name="Beta Foods LLC", country="Canada")
    add_buyer(session, "BUY-THREE", company_name="Gamma Foods LLC", country="United States")

    filtered = client.get(
        "/api/v1/buyers",
        params={"country": "United States", "verification_status": "unverified", "limit": 1, "offset": 0},
    )
    search = client.get("/api/v1/buyers", params={"company_name": "beta"})
    requirements_404 = client.get("/api/v1/buyers/BUY-MISSING/requirements")

    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["country"] == "United States"
    assert search.status_code == 200
    assert [row["buyer_id"] for row in search.json()] == ["BUY-TWO"]
    assert requirements_404.status_code == 404


def test_posted_at_preserved_on_requirement(session: Session) -> None:
    observation = make_observation(session, request_id="REQ-POSTED")
    accept(session, observation)

    result = BuyerCanonicalizationService(session).canonicalize_observation(observation.observation_id)

    requirement = session.get(BuyerRequirement, result.requirement_id)
    assert requirement is not None
    assert isinstance(requirement.posted_at, datetime)
    assert requirement.posted_at == observation.posted_at
