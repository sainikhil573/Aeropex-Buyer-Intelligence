from __future__ import annotations

import pytest
from aeropex_api.core.config import Settings
from aeropex_api.db.base import Base, import_models
from aeropex_api.db.models import (
    AuditEvent,
    Buyer,
    Contact,
    EnrichmentResult,
    SourceObservation,
    VerificationEvidence,
    VerificationResult,
)
from aeropex_api.db.session import get_db_session
from aeropex_api.main import create_app
from aeropex_api.services.buyer_canonicalization import normalize_company_name
from aeropex_api.services.buyer_verification import BuyerVerificationService
from aeropex_api.services.run_lifecycle import utc_now
from aeropex_contracts.enums import (
    EnrichmentStatus,
    VerificationClaimType,
    VerificationStatus,
    VerificationType,
)
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


def add_buyer(session: Session, buyer_id: str = "BUY-VERIFY") -> Buyer:
    now = utc_now()
    buyer = Buyer(
        buyer_id=buyer_id,
        company_name="Example Foods LLC",
        normalized_company_name=normalize_company_name("Example Foods LLC") or "example foods",
        country="United States",
        website=None,
        primary_domain=None,
        company_type=None,
        verification_status=VerificationStatus.UNVERIFIED,
        confidence_score=None,
        created_at=now,
        updated_at=now,
    )
    session.add(buyer)
    session.commit()
    return buyer


def fixture_payload() -> dict[str, object]:
    return {
        "company_exists": True,
        "business_relevance": True,
        "website": "https://Example.com",
        "primary_domain": "www.example.com",
        "general_email": " Procurement@Example.com ",
        "phone": "+1-555-0100",
        "evidence": [
            {
                "source_type": "controlled_fixture",
                "source_url": "https://controlled-fixture.local/company",
                "claim_type": "company_exists",
                "claim_value": "Example Foods LLC",
                "supports_claim": True,
                "evidence_text": "Controlled fixture confirms company record.",
            },
            {
                "source_type": "controlled_fixture",
                "source_url": "https://controlled-fixture.local/domain",
                "claim_type": "domain_association",
                "claim_value": "example.com",
                "supports_claim": True,
                "evidence_text": "Controlled fixture associates the domain.",
            },
        ],
    }


def test_controlled_fixture_creates_pending_verification_evidence_contact_and_enrichment(
    session: Session,
) -> None:
    buyer = add_buyer(session)

    result = BuyerVerificationService(session).create_controlled_test_verification(
        buyer.buyer_id,
        fixture_payload(),
    )

    session.refresh(buyer)
    assert result.status == VerificationStatus.PENDING
    assert result.verification_type == VerificationType.COMPANY
    assert buyer.verification_status == VerificationStatus.UNVERIFIED
    assert result.confidence_score is None

    evidence = session.query(VerificationEvidence).order_by(VerificationEvidence.evidence_id).all()
    assert len(evidence) == 2
    assert {row.claim_type for row in evidence} == {
        VerificationClaimType.COMPANY_EXISTS,
        VerificationClaimType.DOMAIN_ASSOCIATION,
    }
    assert evidence[0].source_url.startswith("https://controlled-fixture.local/")

    contact = session.query(Contact).one()
    assert contact.email == "procurement@example.com"
    assert contact.name is None
    assert contact.title is None
    assert contact.verification_status == VerificationStatus.UNVERIFIED

    enrichments = {row.field_name: row for row in session.query(EnrichmentResult).all()}
    assert enrichments["website"].field_value == "https://example.com"
    assert enrichments["primary_domain"].field_value == "example.com"
    assert enrichments["general_email"].status == EnrichmentStatus.DISCOVERED
    assert enrichments["phone"].source_url == "https://controlled-fixture.local/company"


def test_human_review_syncs_buyer_status_and_preserves_evidence(session: Session) -> None:
    buyer = add_buyer(session)
    service = BuyerVerificationService(session)
    result = service.create_controlled_test_verification(buyer.buyer_id, fixture_payload())
    evidence_ids = {row.evidence_id for row in session.query(VerificationEvidence).all()}

    updated = service.update_review(
        buyer.buyer_id,
        result.verification_id,
        status=VerificationStatus.PARTIALLY_VERIFIED,
        summary="Company exists, domain still needs stronger confirmation.",
    )
    verified = service.update_review(
        buyer.buyer_id,
        result.verification_id,
        status=VerificationStatus.VERIFIED,
        summary="Human reviewed sufficient company and domain evidence.",
    )

    session.refresh(buyer)
    assert updated.reviewed_at is not None
    assert verified.status == VerificationStatus.VERIFIED
    assert buyer.verification_status == VerificationStatus.VERIFIED
    assert {row.evidence_id for row in session.query(VerificationEvidence).all()} == evidence_ids
    assert {event.action for event in session.query(AuditEvent).all()} >= {
        "verification_created",
        "verification_status_updated",
        "buyer_verification_status_updated",
    }


def test_rejected_review_syncs_buyer_status(session: Session) -> None:
    buyer = add_buyer(session)
    result = BuyerVerificationService(session).create_controlled_test_verification(
        buyer.buyer_id,
        fixture_payload(),
    )

    BuyerVerificationService(session).update_review(
        buyer.buyer_id,
        result.verification_id,
        status=VerificationStatus.REJECTED,
        summary="Contradiction found.",
    )

    session.refresh(buyer)
    assert buyer.verification_status == VerificationStatus.REJECTED


def test_same_buyer_same_normalized_email_dedupes_but_other_buyer_allows_same_email(
    session: Session,
) -> None:
    first = add_buyer(session, "BUY-FIRST")
    second = add_buyer(session, "BUY-SECOND")
    service = BuyerVerificationService(session)

    service.create_controlled_test_verification(first.buyer_id, fixture_payload())
    service.create_controlled_test_verification(first.buyer_id, fixture_payload())
    service.create_controlled_test_verification(second.buyer_id, fixture_payload())

    assert session.query(Contact).filter(Contact.buyer_id == first.buyer_id).count() == 1
    assert session.query(Contact).filter(Contact.buyer_id == second.buyer_id).count() == 1


def test_missing_buyer_and_invalid_status_are_rejected(client: TestClient, session: Session) -> None:
    buyer = add_buyer(session)
    response = client.post("/api/v1/buyers/BUY-MISSING/verification/test", json=fixture_payload())
    invalid = client.patch(
        f"/api/v1/buyers/{buyer.buyer_id}/verification/VRF-MISSING",
        json={"status": "accepted"},
    )

    assert response.status_code == 404
    assert invalid.status_code == 422


def test_verification_api_flow(client: TestClient, session: Session) -> None:
    buyer = add_buyer(session)

    created = client.post(f"/api/v1/buyers/{buyer.buyer_id}/verification/test", json=fixture_payload())
    assert created.status_code == 201
    verification_id = created.json()["verification_id"]
    assert created.json()["status"] == "pending"

    state = client.get(f"/api/v1/buyers/{buyer.buyer_id}/verification")
    evidence = client.get(f"/api/v1/buyers/{buyer.buyer_id}/verification/evidence")
    contacts = client.get(f"/api/v1/buyers/{buyer.buyer_id}/contacts")
    enrichments = client.get(f"/api/v1/buyers/{buyer.buyer_id}/enrichments")
    reviewed = client.patch(
        f"/api/v1/buyers/{buyer.buyer_id}/verification/{verification_id}",
        json={"status": "verified", "summary": "Human reviewed."},
    )

    assert state.status_code == 200
    assert state.json()["buyer"]["verification_status"] == "unverified"
    assert len(evidence.json()) == 2
    assert contacts.json()[0]["email"] == "procurement@example.com"
    assert {row["field_name"] for row in enrichments.json()} >= {"website", "phone"}
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "verified"
    assert client.get(f"/api/v1/buyers/{buyer.buyer_id}").json()["verification_status"] == "verified"


def test_source_observation_evidence_remains_untouched(session: Session) -> None:
    buyer = add_buyer(session)
    now = utc_now()
    observation = SourceObservation(
        observation_id="OBS-IMMUTABLE",
        source_id="SRC-X",
        run_id="RUN-X",
        captured_at=now,
        raw_text="Original discovery evidence",
        extraction_status="partial",
        extractor_type="fixture",
    )
    session.add(observation)
    session.commit()

    BuyerVerificationService(session).create_controlled_test_verification(
        buyer.buyer_id,
        {**fixture_payload(), "source_observation_id": observation.observation_id},
    )

    session.refresh(observation)
    assert observation.raw_text == "Original discovery evidence"
    assert observation.buyer_id is None


def test_contact_persistence_failure_rolls_back_verification(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    buyer = add_buyer(session)

    def fail_contact(*args: object, **kwargs: object) -> None:
        raise RuntimeError("contact failure")

    monkeypatch.setattr(BuyerVerificationService, "_create_or_reuse_contact_from_payload", fail_contact)

    with pytest.raises(RuntimeError):
        BuyerVerificationService(session).create_controlled_test_verification(buyer.buyer_id, fixture_payload())

    assert session.query(VerificationResult).count() == 0
    assert session.query(VerificationEvidence).count() == 0
    assert session.query(Contact).count() == 0


def test_enrichment_persistence_failure_rolls_back_verification(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    buyer = add_buyer(session)

    def fail_enrichment(*args: object, **kwargs: object) -> None:
        raise RuntimeError("enrichment failure")

    monkeypatch.setattr(BuyerVerificationService, "_create_enrichments", fail_enrichment)

    with pytest.raises(RuntimeError):
        BuyerVerificationService(session).create_controlled_test_verification(buyer.buyer_id, fixture_payload())

    assert session.query(VerificationResult).count() == 0
    assert session.query(VerificationEvidence).count() == 0
    assert session.query(Contact).count() == 0
