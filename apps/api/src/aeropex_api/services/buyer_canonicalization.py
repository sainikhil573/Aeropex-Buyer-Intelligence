"""Canonical buyer entity resolution and observation canonicalization."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from aeropex_contracts.enums import (
    BuyerRequirementStatus,
    EntityResolutionStatus,
    ObservationReviewStatus,
    VerificationStatus,
)
from aeropex_contracts.models import CanonicalizationResult
from sqlalchemy import func
from sqlalchemy.orm import Session

from aeropex_api.db.models import (
    AuditEvent,
    Buyer,
    BuyerRequirement,
    ObservationReview,
    SourceObservation,
)
from aeropex_api.services.observation_review import DEFAULT_REVIEW_ACTOR
from aeropex_api.services.run_lifecycle import make_id, utc_now

LEGAL_SUFFIX_PATTERN = re.compile(
    r"\b(l\.?\s*l\.?\s*c\.?|inc\.?|corporation|corp\.?|ltd\.?|limited|pvt\.?\s+ltd\.?|private\s+limited)\b",
    re.IGNORECASE,
)


class ObservationNotFoundError(ValueError):
    """Raised when canonicalization references a missing observation."""


class BuyerCanonicalizationService:
    """Progress accepted observations into conservative canonical buyer entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def canonicalize_observation(
        self,
        observation_id: str,
        *,
        actor_id: str = DEFAULT_REVIEW_ACTOR,
    ) -> CanonicalizationResult:
        observation = self.session.get(SourceObservation, observation_id)
        if observation is None:
            raise ObservationNotFoundError(observation_id)

        if observation.buyer_id is not None:
            return CanonicalizationResult(
                status=EntityResolutionStatus.ALREADY_CANONICALIZED,
                observation_id=observation.observation_id,
                buyer_id=observation.buyer_id,
                requirement_id=observation.requirement_id,
                matched_existing_buyer=True,
                reason="Observation already has canonical linkage metadata.",
            )

        review = self._review_for(observation.observation_id)
        if review is None or review.status != ObservationReviewStatus.ACCEPTED:
            return CanonicalizationResult(
                status=EntityResolutionStatus.INELIGIBLE,
                observation_id=observation.observation_id,
                reason="Observation review status must be accepted.",
            )

        normalized_name = normalize_company_name(observation.company_name)
        if normalized_name is None:
            return CanonicalizationResult(
                status=EntityResolutionStatus.INELIGIBLE,
                observation_id=observation.observation_id,
                reason="Observation does not include a usable company_name.",
            )

        resolution = self._resolve_buyer(observation, normalized_name)
        if resolution.status == EntityResolutionStatus.AMBIGUOUS:
            self._audit(
                action="entity_resolution_ambiguous",
                observation_id=observation.observation_id,
                buyer_id=None,
                requirement_id=None,
                before_state=self._linkage_state(observation),
                after_state={
                    "candidate_buyer_ids": resolution.candidate_buyer_ids,
                    "reason": resolution.reason,
                },
                actor_id=actor_id,
            )
            self.session.commit()
            return resolution

        before_state = self._linkage_state(observation)
        try:
            matched_existing = resolution.status == EntityResolutionStatus.MATCHED
            buyer = self.session.get(Buyer, resolution.buyer_id) if matched_existing else None
            if buyer is None:
                buyer = self._create_buyer(observation, normalized_name)
                resolution.status = EntityResolutionStatus.CREATED
                resolution.buyer_id = buyer.buyer_id
                self._audit(
                    action="buyer_created",
                    observation_id=observation.observation_id,
                    buyer_id=buyer.buyer_id,
                    requirement_id=None,
                    before_state=None,
                    after_state=self._buyer_state(buyer),
                    actor_id=actor_id,
                )
            else:
                self._audit(
                    action="buyer_matched",
                    observation_id=observation.observation_id,
                    buyer_id=buyer.buyer_id,
                    requirement_id=None,
                    before_state=None,
                    after_state={"resolution_reason": resolution.reason},
                    actor_id=actor_id,
                )

            requirement = self._create_requirement_if_supported(observation, buyer)
            if requirement is not None:
                self._audit(
                    action="buyer_requirement_created",
                    observation_id=observation.observation_id,
                    buyer_id=buyer.buyer_id,
                    requirement_id=requirement.requirement_id,
                    before_state=None,
                    after_state=self._requirement_state(requirement),
                    actor_id=actor_id,
                )

            self._link_observation(observation, buyer, requirement)
            self._audit(
                action="source_observation_linked",
                observation_id=observation.observation_id,
                buyer_id=buyer.buyer_id,
                requirement_id=requirement.requirement_id if requirement else None,
                before_state=before_state,
                after_state=self._linkage_state(observation),
                actor_id=actor_id,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        self.session.refresh(observation)
        return CanonicalizationResult(
            status=resolution.status,
            observation_id=observation.observation_id,
            buyer_id=buyer.buyer_id,
            requirement_id=requirement.requirement_id if requirement else None,
            matched_existing_buyer=matched_existing,
            reason=resolution.reason,
        )

    def list_buyers(
        self,
        *,
        limit: int,
        offset: int,
        country: str | None = None,
        verification_status: VerificationStatus | None = None,
        company_name: str | None = None,
    ) -> list[Buyer]:
        query = self.session.query(Buyer)
        if country:
            query = query.filter(func.lower(Buyer.country) == normalize_country(country))
        if verification_status:
            query = query.filter(Buyer.verification_status == verification_status)
        if company_name:
            query = query.filter(Buyer.normalized_company_name.contains(normalize_company_name(company_name) or ""))
        return query.order_by(Buyer.created_at.desc(), Buyer.buyer_id.desc()).offset(offset).limit(limit).all()

    def get_buyer(self, buyer_id: str) -> Buyer | None:
        return self.session.get(Buyer, buyer_id)

    def list_requirements(self, buyer_id: str, *, limit: int, offset: int) -> list[BuyerRequirement]:
        return (
            self.session.query(BuyerRequirement)
            .filter(BuyerRequirement.buyer_id == buyer_id)
            .order_by(BuyerRequirement.created_at.desc(), BuyerRequirement.requirement_id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_requirement(self, requirement_id: str) -> BuyerRequirement | None:
        return self.session.get(BuyerRequirement, requirement_id)

    def _resolve_buyer(self, observation: SourceObservation, normalized_name: str) -> CanonicalizationResult:
        primary_domain = extract_primary_domain(observation)
        if primary_domain:
            domain_matches = (
                self.session.query(Buyer)
                .filter(func.lower(Buyer.primary_domain) == primary_domain)
                .order_by(Buyer.buyer_id)
                .all()
            )
            if len(domain_matches) == 1:
                return CanonicalizationResult(
                    status=EntityResolutionStatus.MATCHED,
                    observation_id=observation.observation_id,
                    buyer_id=domain_matches[0].buyer_id,
                    matched_existing_buyer=True,
                    reason="Matched by exact normalized primary_domain.",
                )
            if len(domain_matches) > 1:
                return CanonicalizationResult(
                    status=EntityResolutionStatus.AMBIGUOUS,
                    observation_id=observation.observation_id,
                    candidate_buyer_ids=[buyer.buyer_id for buyer in domain_matches],
                    reason="Multiple buyers share the same normalized primary_domain.",
                )

        normalized_country = normalize_country(observation.country)
        if normalized_country:
            name_country_matches = (
                self.session.query(Buyer)
                .filter(
                    Buyer.normalized_company_name == normalized_name,
                    func.lower(Buyer.country) == normalized_country,
                )
                .order_by(Buyer.buyer_id)
                .all()
            )
            if len(name_country_matches) == 1:
                return CanonicalizationResult(
                    status=EntityResolutionStatus.MATCHED,
                    observation_id=observation.observation_id,
                    buyer_id=name_country_matches[0].buyer_id,
                    matched_existing_buyer=True,
                    reason="Matched by exact normalized company name and country.",
                )
            if len(name_country_matches) > 1:
                return CanonicalizationResult(
                    status=EntityResolutionStatus.AMBIGUOUS,
                    observation_id=observation.observation_id,
                    candidate_buyer_ids=[buyer.buyer_id for buyer in name_country_matches],
                    reason="Multiple buyers share exact normalized company name and country.",
                )

        return CanonicalizationResult(
            status=EntityResolutionStatus.CREATED,
            observation_id=observation.observation_id,
            reason="No deterministic existing buyer match.",
        )

    def _create_buyer(self, observation: SourceObservation, normalized_name: str) -> Buyer:
        now = utc_now()
        buyer = Buyer(
            buyer_id=make_id("BUY"),
            company_name=observation.company_name.strip() if observation.company_name else normalized_name,
            normalized_company_name=normalized_name,
            country=clean_text(observation.country),
            website=extract_website(observation),
            primary_domain=extract_primary_domain(observation),
            company_type=None,
            verification_status=VerificationStatus.UNVERIFIED,
            confidence_score=None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(buyer)
        self.session.flush()
        return buyer

    def _create_requirement_if_supported(
        self,
        observation: SourceObservation,
        buyer: Buyer,
    ) -> BuyerRequirement | None:
        requirement_text = clean_text(observation.requirement_text)
        if requirement_text is None:
            return None

        now = utc_now()
        requirement = BuyerRequirement(
            requirement_id=make_id("BRQ"),
            buyer_id=buyer.buyer_id,
            product_id=clean_text(observation.product_id),
            requirement_text=requirement_text,
            quantity=observation.quantity,
            unit=clean_text(observation.unit),
            specifications=dict(observation.specifications or {}),
            destination=None,
            posted_at=observation.posted_at,
            status=BuyerRequirementStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self.session.add(requirement)
        self.session.flush()
        return requirement

    def _link_observation(
        self,
        observation: SourceObservation,
        buyer: Buyer,
        requirement: BuyerRequirement | None,
    ) -> None:
        observation.buyer_id = buyer.buyer_id
        observation.requirement_id = requirement.requirement_id if requirement else None
        self.session.flush()

    def _review_for(self, observation_id: str) -> ObservationReview | None:
        return (
            self.session.query(ObservationReview)
            .filter(ObservationReview.observation_id == observation_id)
            .one_or_none()
        )

    def _audit(
        self,
        *,
        action: str,
        observation_id: str,
        buyer_id: str | None,
        requirement_id: str | None,
        before_state: dict[str, object] | None,
        after_state: dict[str, object] | None,
        actor_id: str,
    ) -> None:
        self.session.add(
            AuditEvent(
                audit_id=make_id("AUD"),
                actor_type="user",
                actor_id=actor_id,
                action=action,
                entity_type="SourceObservation",
                entity_id=observation_id,
                before_state=before_state,
                after_state={
                    **(after_state or {}),
                    "observation_id": observation_id,
                    "buyer_id": buyer_id,
                    "requirement_id": requirement_id,
                },
                timestamp=utc_now(),
            )
        )

    @staticmethod
    def _linkage_state(observation: SourceObservation) -> dict[str, object]:
        return {
            "observation_id": observation.observation_id,
            "buyer_id": observation.buyer_id,
            "requirement_id": observation.requirement_id,
        }

    @staticmethod
    def _buyer_state(buyer: Buyer) -> dict[str, object]:
        return {
            "buyer_id": buyer.buyer_id,
            "company_name": buyer.company_name,
            "normalized_company_name": buyer.normalized_company_name,
            "country": buyer.country,
            "primary_domain": buyer.primary_domain,
            "verification_status": buyer.verification_status.value,
        }

    @staticmethod
    def _requirement_state(requirement: BuyerRequirement) -> dict[str, object]:
        return {
            "requirement_id": requirement.requirement_id,
            "buyer_id": requirement.buyer_id,
            "product_id": requirement.product_id,
            "requirement_text": requirement.requirement_text,
            "quantity": requirement.quantity,
            "unit": requirement.unit,
            "specifications": requirement.specifications,
            "posted_at": requirement.posted_at.isoformat() if requirement.posted_at else None,
            "status": requirement.status.value,
        }


def normalize_company_name(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    lowered = cleaned.lower()
    lowered = re.sub(r"[,&]", " ", lowered)
    lowered = re.sub(r"[^\w\s.]", " ", lowered)
    lowered = LEGAL_SUFFIX_PATTERN.sub(" ", lowered)
    lowered = re.sub(r"\.", " ", lowered)
    normalized = re.sub(r"\s+", " ", lowered).strip()
    return normalized or None


def normalize_country(value: str | None) -> str | None:
    cleaned = clean_text(value)
    return cleaned.lower() if cleaned else None


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def extract_website(observation: SourceObservation) -> str | None:
    metadata = observation.observation_metadata or {}
    for key in ("website", "company_website"):
        value = clean_text(str(metadata[key])) if key in metadata and metadata[key] is not None else None
        if value:
            return value
    return None


def extract_primary_domain(observation: SourceObservation) -> str | None:
    website = extract_website(observation)
    if website is None:
        metadata = observation.observation_metadata or {}
        value = clean_text(str(metadata["primary_domain"])) if metadata.get("primary_domain") else None
        if value:
            return normalize_domain(value)
        return None
    return normalize_domain(website)


def normalize_domain(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned if "://" in cleaned else f"https://{cleaned}")
    host = parsed.netloc or parsed.path
    host = host.lower().split("@")[-1].split(":")[0].strip(".")
    host = host.removeprefix("www.")
    return host or None
