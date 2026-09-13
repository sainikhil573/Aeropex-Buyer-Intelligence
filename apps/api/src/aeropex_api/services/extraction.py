"""Bounded extraction service and SourceObservation persistence."""

from __future__ import annotations

import logging
from time import perf_counter

from aeropex_contracts.enums import ConnectorStatus, ErrorSeverity, ExtractionStatus
from aeropex_contracts.models import (
    ConnectorResult,
    ExtractionRequest,
    ExtractionResult,
    ProductContext,
)
from sqlalchemy.orm import Session, joinedload

from aeropex_api.db.models import AgentRun, ObservationReview, Product, Source, SourceObservation
from aeropex_api.extractors.factory import ExtractorFactory
from aeropex_api.services.run_lifecycle import AgentRunService, make_id, utc_now

logger = logging.getLogger(__name__)

MAX_RAW_TEXT_CHARS = 200_000


class ExtractionService:
    """Turn successful ConnectorResult payloads into immutable observations."""

    def __init__(self, session: Session, *, factory: ExtractorFactory | None = None) -> None:
        self.session = session
        self.factory = factory or ExtractorFactory()
        self.run_service = AgentRunService(session)

    def extract_from_connector_result(self, result: ConnectorResult) -> SourceObservation | None:
        if result.status != ConnectorStatus.SUCCESS:
            return None

        source = self.session.get(Source, result.source_id)
        source_type = source.source_type if source is not None else None
        request = ExtractionRequest(
            request_id=result.request_id,
            run_id=result.run_id,
            source_id=result.source_id,
            source_url=result.target_url,
            content_type=result.content_type,
            raw_content=self._bounded_raw_text(result.raw_content),
            product_context=self._product_context(),
            captured_at=result.retrieved_at,
            source_type=source_type,
        )
        extractor = self.factory.create(content_type=result.content_type, source_type=source_type)
        started_at = perf_counter()
        extraction = extractor.extract(request)
        duration_ms = int((perf_counter() - started_at) * 1000)

        try:
            observation = self._create_observation(extraction)
        except Exception:
            self.session.rollback()
            self._create_error_event(
                extraction,
                error_type="observation_persistence_error",
                message="Failed to persist SourceObservation",
            )
            raise

        if extraction.status == ExtractionStatus.FAILED:
            self._create_error_event(
                extraction,
                error_type=extraction.error_type or "extractor_parse_error",
                message=extraction.error_message or "Extractor failed",
            )

        logger.info(
            "extraction_completed",
            extra={
                "run_id": result.run_id,
                "request_id": result.request_id,
                "source_id": result.source_id,
                "observation_id": observation.observation_id,
                "extractor_type": extraction.extractor_type,
                "extraction_status": extraction.status.value,
                "duration": duration_ms,
                "fields_extracted_count": self._fields_extracted_count(extraction),
                "error_category": extraction.error_type,
            },
        )
        return observation

    def list_observations(
        self,
        *,
        limit: int,
        offset: int,
        source_id: str | None = None,
        run_id: str | None = None,
        product_id: str | None = None,
        extraction_status: ExtractionStatus | None = None,
        review_status: object | None = None,
    ) -> list[SourceObservation]:
        query = self.session.query(SourceObservation).options(joinedload(SourceObservation.review))
        if source_id:
            query = query.filter(SourceObservation.source_id == source_id)
        if run_id:
            query = query.filter(SourceObservation.run_id == run_id)
        if product_id:
            query = query.filter(SourceObservation.product_id == product_id)
        if extraction_status:
            query = query.filter(SourceObservation.extraction_status == extraction_status)
        if review_status:
            from aeropex_contracts.enums import ObservationReviewStatus

            if review_status == ObservationReviewStatus.UNREVIEWED:
                query = query.outerjoin(ObservationReview).filter(
                    (ObservationReview.review_id.is_(None))
                    | (ObservationReview.status == ObservationReviewStatus.UNREVIEWED)
                )
            else:
                query = query.join(ObservationReview).filter(ObservationReview.status == review_status)
        return (
            query.order_by(SourceObservation.captured_at.desc(), SourceObservation.observation_id.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 100))
            .all()
        )

    def get_observation(self, observation_id: str) -> SourceObservation | None:
        return self.session.get(SourceObservation, observation_id)

    def _create_observation(self, extraction: ExtractionResult) -> SourceObservation:
        observation = SourceObservation(
            observation_id=make_id("OBS"),
            source_id=extraction.source_id,
            run_id=extraction.run_id,
            source_url=extraction.source_url,
            captured_at=utc_now(),
            raw_text=self._bounded_raw_text(extraction.raw_text),
            evidence_type=extraction.evidence_type,
            confidence_score=float(extraction.confidence_score) if extraction.confidence_score is not None else None,
            buyer_id=None,
            requirement_id=None,
            product_id=extraction.product_id,
            company_name=self._clean_text(extraction.company_name),
            country=self._clean_text(extraction.country),
            requirement_text=self._clean_text(extraction.requirement_text),
            quantity=float(extraction.quantity) if extraction.quantity is not None else None,
            unit=self._clean_text(extraction.unit),
            specifications=extraction.specifications,
            contact_name=self._clean_text(extraction.contact_name),
            contact_email=self._clean_text(extraction.contact_email).lower()
            if self._clean_text(extraction.contact_email)
            else None,
            contact_phone=self._clean_text(extraction.contact_phone),
            posted_at=extraction.posted_at,
            extraction_status=extraction.status,
            extractor_type=extraction.extractor_type,
            observation_metadata={
                "request_id": extraction.request_id,
                "product_name": extraction.product_name,
                "error_type": extraction.error_type,
                "error_message": extraction.error_message,
            },
        )
        self.session.add(observation)
        self.session.commit()
        self.session.refresh(observation)
        return observation

    def _create_error_event(self, extraction: ExtractionResult, *, error_type: str, message: str) -> None:
        run = self.session.get(AgentRun, extraction.run_id)
        self.run_service.create_error_event(
            run_id=extraction.run_id if run is not None else None,
            agent_id=run.agent_id if run is not None else None,
            error_type=error_type,
            severity=ErrorSeverity.ERROR,
            message=message,
            retryable=False,
            resolved=False,
        )

    def _product_context(self) -> list[ProductContext]:
        products = self.session.query(Product).filter(Product.active.is_(True)).all()
        return [
            ProductContext(
                product_id=product.product_id,
                name=product.name,
                aliases=product.aliases,
                variants=product.variants,
            )
            for product in products
        ]

    @staticmethod
    def _bounded_raw_text(value: str | None) -> str | None:
        if value is None:
            return None
        return value[:MAX_RAW_TEXT_CHARS]

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _fields_extracted_count(extraction: ExtractionResult) -> int:
        fields = (
            extraction.company_name,
            extraction.country,
            extraction.product_id,
            extraction.requirement_text,
            extraction.quantity,
            extraction.unit,
            extraction.contact_name,
            extraction.contact_email,
            extraction.contact_phone,
            extraction.posted_at,
        )
        return sum(value is not None for value in fields)
