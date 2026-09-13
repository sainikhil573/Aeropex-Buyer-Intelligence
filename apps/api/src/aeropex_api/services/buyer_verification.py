"""Buyer verification and contact enrichment workflow."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from aeropex_contracts.enums import (
    ContactType,
    EnrichmentStatus,
    VerificationClaimType,
    VerificationStatus,
    VerificationType,
)
from sqlalchemy.orm import Session

from aeropex_api.db.models import (
    AuditEvent,
    Buyer,
    Contact,
    EnrichmentResult,
    VerificationEvidence,
    VerificationResult,
)
from aeropex_api.services.observation_review import DEFAULT_REVIEW_ACTOR
from aeropex_api.services.run_lifecycle import make_id, utc_now

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class BuyerNotFoundError(ValueError):
    """Raised when verification references a missing buyer."""


class VerificationNotFoundError(ValueError):
    """Raised when a verification result is missing or belongs to another buyer."""


class BuyerVerificationService:
    """Persist evidence-backed buyer verification and enrichment state."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def current_state(self, buyer_id: str) -> dict[str, list[object] | Buyer]:
        buyer = self._require_buyer(buyer_id)
        return {
            "buyer": buyer,
            "verification_results": self.list_verifications(buyer_id, limit=50, offset=0),
            "contacts": self.list_contacts(buyer_id, limit=50, offset=0),
            "enrichments": self.list_enrichments(buyer_id, limit=50, offset=0),
            "evidence": self.list_evidence(buyer_id, limit=100, offset=0),
        }

    def create_controlled_test_verification(
        self,
        buyer_id: str,
        payload: dict[str, Any],
        *,
        actor_id: str = DEFAULT_REVIEW_ACTOR,
    ) -> VerificationResult:
        buyer = self._require_buyer(buyer_id)
        now = utc_now()
        try:
            result = VerificationResult(
                verification_id=make_id("VRF"),
                buyer_id=buyer.buyer_id,
                status=VerificationStatus.PENDING,
                verification_type=VerificationType.COMPANY,
                summary="Controlled verification fixture created for human review.",
                confidence_score=None,
                reviewed_by=None,
                reviewed_at=None,
                risk_flags={},
                checks={
                    "company_exists": payload.get("company_exists"),
                    "business_relevance": payload.get("business_relevance"),
                    "external_research": False,
                },
                created_at=now,
                updated_at=now,
            )
            self.session.add(result)
            self.session.flush()
            self._audit(
                action="verification_created",
                entity_type="VerificationResult",
                entity_id=result.verification_id,
                before_state=None,
                after_state=self._verification_state(result),
                actor_id=actor_id,
            )

            self._create_evidence_rows(result, payload)
            contact = self._create_or_reuse_contact_from_payload(buyer.buyer_id, payload, actor_id=actor_id)
            self._create_enrichments(result, payload, contact, actor_id=actor_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        self.session.refresh(result)
        return result

    def update_review(
        self,
        buyer_id: str,
        verification_id: str,
        *,
        status: VerificationStatus,
        summary: str | None,
        reviewed_by: str | None = None,
        actor_id: str = DEFAULT_REVIEW_ACTOR,
    ) -> VerificationResult:
        buyer = self._require_buyer(buyer_id)
        result = self._require_verification(buyer_id, verification_id)
        before_result = self._verification_state(result)
        before_buyer = self._buyer_status_state(buyer)
        now = utc_now()
        try:
            result.status = status
            result.summary = summary
            result.reviewed_by = reviewed_by or actor_id
            result.reviewed_at = now
            result.updated_at = now
            buyer.verification_status = status
            buyer.updated_at = now
            self.session.flush()
            self._audit(
                action="verification_status_updated",
                entity_type="VerificationResult",
                entity_id=result.verification_id,
                before_state=before_result,
                after_state=self._verification_state(result),
                actor_id=actor_id,
            )
            self._audit(
                action="buyer_verification_status_updated",
                entity_type="Buyer",
                entity_id=buyer.buyer_id,
                before_state=before_buyer,
                after_state=self._buyer_status_state(buyer),
                actor_id=actor_id,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        self.session.refresh(result)
        return result

    def list_verifications(self, buyer_id: str, *, limit: int, offset: int) -> list[VerificationResult]:
        self._require_buyer(buyer_id)
        return (
            self.session.query(VerificationResult)
            .filter(VerificationResult.buyer_id == buyer_id)
            .order_by(VerificationResult.created_at.desc(), VerificationResult.verification_id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_evidence(self, buyer_id: str, *, limit: int, offset: int) -> list[VerificationEvidence]:
        self._require_buyer(buyer_id)
        return (
            self.session.query(VerificationEvidence)
            .filter(VerificationEvidence.buyer_id == buyer_id)
            .order_by(VerificationEvidence.captured_at.desc(), VerificationEvidence.evidence_id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_contacts(self, buyer_id: str, *, limit: int, offset: int) -> list[Contact]:
        self._require_buyer(buyer_id)
        return (
            self.session.query(Contact)
            .filter(Contact.buyer_id == buyer_id)
            .order_by(Contact.created_at.desc(), Contact.contact_id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_enrichments(self, buyer_id: str, *, limit: int, offset: int) -> list[EnrichmentResult]:
        self._require_buyer(buyer_id)
        return (
            self.session.query(EnrichmentResult)
            .filter(EnrichmentResult.buyer_id == buyer_id)
            .order_by(EnrichmentResult.created_at.desc(), EnrichmentResult.enrichment_id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def _create_evidence_rows(self, result: VerificationResult, payload: dict[str, Any]) -> None:
        evidence_rows = payload.get("evidence") or []
        for row in evidence_rows:
            evidence = VerificationEvidence(
                evidence_id=make_id("VEV"),
                verification_id=result.verification_id,
                buyer_id=result.buyer_id,
                source_type=clean_text(row.get("source_type")) or "controlled_fixture",
                source_url=clean_text(row.get("source_url")),
                evidence_text=clean_text(row.get("evidence_text")) or "",
                captured_at=utc_now(),
                claim_type=VerificationClaimType(row.get("claim_type", VerificationClaimType.OTHER)),
                claim_value=clean_text(row.get("claim_value")),
                supports_claim=row.get("supports_claim"),
                evidence_metadata=dict(row.get("metadata") or {}),
            )
            self.session.add(evidence)
            self.session.flush()
            self._audit(
                action="verification_evidence_added",
                entity_type="VerificationEvidence",
                entity_id=evidence.evidence_id,
                before_state=None,
                after_state={
                    "verification_id": evidence.verification_id,
                    "buyer_id": evidence.buyer_id,
                    "claim_type": evidence.claim_type.value,
                    "source_type": evidence.source_type,
                },
            )

    def _create_or_reuse_contact_from_payload(
        self,
        buyer_id: str,
        payload: dict[str, Any],
        *,
        actor_id: str,
    ) -> Contact | None:
        email = normalize_email(payload.get("contact_email") or payload.get("general_email"))
        phone = clean_text(payload.get("contact_phone") or payload.get("phone"))
        normalized_phone = normalize_phone(phone)
        name = clean_text(payload.get("contact_name"))
        title = clean_text(payload.get("contact_title"))
        if email is None and phone is None and name is None:
            return None

        existing = None
        if email:
            existing = (
                self.session.query(Contact)
                .filter(Contact.buyer_id == buyer_id, Contact.normalized_email == email)
                .one_or_none()
            )
        if existing is None and normalized_phone:
            existing = (
                self.session.query(Contact)
                .filter(Contact.buyer_id == buyer_id, Contact.normalized_phone == normalized_phone)
                .one_or_none()
            )
        if existing is not None:
            return existing

        now = utc_now()
        contact = Contact(
            contact_id=make_id("CON"),
            buyer_id=buyer_id,
            name=name,
            email=email,
            normalized_email=email,
            phone=phone,
            normalized_phone=normalized_phone,
            title=title,
            department=clean_text(payload.get("contact_department")),
            contact_type=ContactType(payload.get("contact_type", ContactType.GENERAL)),
            verification_status=VerificationStatus.UNVERIFIED,
            source_observation_id=clean_text(payload.get("source_observation_id")),
            created_at=now,
            updated_at=now,
        )
        self.session.add(contact)
        self.session.flush()
        self._audit(
            action="contact_created",
            entity_type="Contact",
            entity_id=contact.contact_id,
            before_state=None,
            after_state=self._contact_state(contact),
            actor_id=actor_id,
        )
        return contact

    def _create_enrichments(
        self,
        result: VerificationResult,
        payload: dict[str, Any],
        contact: Contact | None,
        *,
        actor_id: str,
    ) -> None:
        source_type = "controlled_fixture"
        source_url = clean_text(payload.get("source_url")) or self._first_evidence_url(payload)
        fields = {
            "website": normalize_website(payload.get("website")),
            "primary_domain": normalize_domain(payload.get("primary_domain")),
            "general_email": normalize_email(payload.get("general_email")),
            "phone": clean_text(payload.get("phone")),
            "contact_name": clean_text(payload.get("contact_name")),
            "contact_email": normalize_email(payload.get("contact_email")),
            "contact_phone": clean_text(payload.get("contact_phone")),
            "contact_title": clean_text(payload.get("contact_title")),
            "address": clean_text(payload.get("address")),
        }
        for field_name, value in fields.items():
            if value is None:
                continue
            enrichment = EnrichmentResult(
                enrichment_id=make_id("ENR"),
                buyer_id=result.buyer_id,
                contact_id=contact.contact_id if contact and field_name.startswith("contact_") else None,
                field_name=field_name,
                field_value=value,
                source_type=source_type,
                source_url=source_url,
                captured_at=utc_now(),
                status=EnrichmentStatus.DISCOVERED,
                created_at=utc_now(),
            )
            self.session.add(enrichment)
            self.session.flush()
            self._audit(
                action="enrichment_created",
                entity_type="EnrichmentResult",
                entity_id=enrichment.enrichment_id,
                before_state=None,
                after_state={
                    "buyer_id": enrichment.buyer_id,
                    "contact_id": enrichment.contact_id,
                    "field_name": enrichment.field_name,
                    "status": enrichment.status.value,
                },
                actor_id=actor_id,
            )

    def _require_buyer(self, buyer_id: str) -> Buyer:
        buyer = self.session.get(Buyer, buyer_id)
        if buyer is None:
            raise BuyerNotFoundError(buyer_id)
        return buyer

    def _require_verification(self, buyer_id: str, verification_id: str) -> VerificationResult:
        result = self.session.get(VerificationResult, verification_id)
        if result is None or result.buyer_id != buyer_id:
            raise VerificationNotFoundError(verification_id)
        return result

    def _audit(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        before_state: dict[str, Any] | None,
        after_state: dict[str, Any] | None,
        actor_id: str = DEFAULT_REVIEW_ACTOR,
    ) -> None:
        self.session.add(
            AuditEvent(
                audit_id=make_id("AUD"),
                actor_type="user",
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=before_state,
                after_state=after_state,
                timestamp=utc_now(),
            )
        )

    @staticmethod
    def _verification_state(result: VerificationResult) -> dict[str, Any]:
        return {
            "verification_id": result.verification_id,
            "buyer_id": result.buyer_id,
            "status": result.status.value,
            "verification_type": result.verification_type.value,
            "summary": result.summary,
            "reviewed_by": result.reviewed_by,
            "reviewed_at": result.reviewed_at.isoformat() if result.reviewed_at else None,
        }

    @staticmethod
    def _buyer_status_state(buyer: Buyer) -> dict[str, Any]:
        return {"buyer_id": buyer.buyer_id, "verification_status": buyer.verification_status.value}

    @staticmethod
    def _contact_state(contact: Contact) -> dict[str, Any]:
        return {
            "contact_id": contact.contact_id,
            "buyer_id": contact.buyer_id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "title": contact.title,
            "verification_status": contact.verification_status.value,
        }

    @staticmethod
    def _first_evidence_url(payload: dict[str, Any]) -> str | None:
        for row in payload.get("evidence") or []:
            source_url = clean_text(row.get("source_url"))
            if source_url:
                return source_url
        return None


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def normalize_email(value: object) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    normalized = cleaned.lower()
    if not EMAIL_PATTERN.match(normalized):
        return None
    return normalized


def normalize_phone(value: object) -> str | None:
    cleaned = clean_text(value)
    return cleaned if cleaned else None


def normalize_website(value: object) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned if "://" in cleaned else f"https://{cleaned}")
    if not (parsed.netloc or parsed.path):
        return None
    scheme = parsed.scheme or "https"
    host = (parsed.netloc or parsed.path).lower()
    path = parsed.path if parsed.netloc else ""
    return f"{scheme}://{host}{path}".rstrip("/")


def normalize_domain(value: object) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned if "://" in cleaned else f"https://{cleaned}")
    host = parsed.netloc or parsed.path
    host = host.lower().split("@")[-1].split(":")[0].strip(".")
    host = host.removeprefix("www.")
    return host or None
