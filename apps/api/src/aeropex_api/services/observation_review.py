"""Observation review workflow service."""

from __future__ import annotations

import logging

from aeropex_contracts.enums import ObservationReviewStatus
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aeropex_api.db.models import AuditEvent, ObservationReview, SourceObservation
from aeropex_api.services.run_lifecycle import make_id, utc_now

logger = logging.getLogger(__name__)

DEFAULT_REVIEW_ACTOR = "local-admin"


class ObservationNotFoundError(ValueError):
    """Raised when a review references a missing observation."""


class ObservationReviewService:
    """Manage mutable review state while leaving SourceObservation immutable."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_review(self, observation_id: str) -> ObservationReview | None:
        return (
            self.session.query(ObservationReview)
            .filter(ObservationReview.observation_id == observation_id)
            .one_or_none()
        )

    def default_review_state(self, observation_id: str) -> dict[str, object]:
        return {
            "review_id": None,
            "observation_id": observation_id,
            "status": ObservationReviewStatus.UNREVIEWED,
            "review_notes": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "created_at": None,
            "updated_at": None,
        }

    def update_review(
        self,
        observation_id: str,
        *,
        status: ObservationReviewStatus,
        review_notes: str | None,
        actor_id: str = DEFAULT_REVIEW_ACTOR,
    ) -> ObservationReview:
        if self.session.get(SourceObservation, observation_id) is None:
            raise ObservationNotFoundError(observation_id)

        now = utc_now()
        review = self.get_review(observation_id)
        before_state = self._state(review, observation_id)
        if review is None:
            review = ObservationReview(
                review_id=make_id("REV"),
                observation_id=observation_id,
                status=status,
                review_notes=self._clean_notes(review_notes),
                reviewed_by=actor_id,
                reviewed_at=now,
                created_at=now,
                updated_at=now,
            )
            self.session.add(review)
        else:
            review.status = status
            review.review_notes = self._clean_notes(review_notes)
            review.reviewed_by = actor_id
            review.reviewed_at = now
            review.updated_at = now

        after_state = self._state(review, observation_id)
        self.session.add(
            AuditEvent(
                audit_id=make_id("AUD"),
                actor_type="user",
                actor_id=actor_id,
                action="observation_review_updated",
                entity_type="ObservationReview",
                entity_id=observation_id,
                before_state=before_state,
                after_state=after_state,
                timestamp=now,
            )
        )
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
        self.session.refresh(review)
        logger.info(
            "observation_review_updated",
            extra={
                "observation_id": observation_id,
                "review_id": review.review_id,
                "old_status": before_state["status"],
                "new_status": status.value,
                "actor_id": actor_id,
            },
        )
        return review

    def review_counts(self) -> dict[str, int]:
        counts = dict.fromkeys((status.value for status in ObservationReviewStatus), 0)
        rows = (
            self.session.query(ObservationReview.status, SourceObservation.observation_id)
            .join(SourceObservation, SourceObservation.observation_id == ObservationReview.observation_id)
            .all()
        )
        for status, _observation_id in rows:
            counts[status.value] += 1
        reviewed_total = sum(counts.values()) - counts[ObservationReviewStatus.UNREVIEWED.value]
        total_observations = self.session.query(SourceObservation).count()
        counts[ObservationReviewStatus.UNREVIEWED.value] = max(total_observations - reviewed_total, 0)
        return counts

    def _state(self, review: ObservationReview | None, observation_id: str) -> dict[str, object]:
        if review is None:
            return self.default_review_state(observation_id)
        return {
            "review_id": review.review_id,
            "observation_id": review.observation_id,
            "status": review.status.value,
            "review_notes": review.review_notes,
            "reviewed_by": review.reviewed_by,
            "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
            "created_at": review.created_at.isoformat() if review.created_at else None,
            "updated_at": review.updated_at.isoformat() if review.updated_at else None,
        }

    @staticmethod
    def _clean_notes(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
