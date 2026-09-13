"""Operational state persistence models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aeropex_contracts.enums import (
    AgentStatus,
    AuthorityLevel,
    ErrorSeverity,
    EvidenceType,
    ExtractionStatus,
    RunStatus,
    TriggerType,
)
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator

from aeropex_api.db.base import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class UTCDateTime(TypeDecorator[datetime]):
    """Persist datetimes as timezone-aware UTC values."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("datetime values must be timezone-aware")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def enum_values(enum_class: type) -> list[str]:
    return [member.value for member in enum_class]


class Agent(Base):
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(json_type, nullable=False, default=list)
    authority_level: Mapped[AuthorityLevel] = mapped_column(
        Enum(AuthorityLevel, values_callable=enum_values, native_enum=False, length=16),
        nullable=False,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    runs: Mapped[list[AgentRun]] = relationship(back_populates="agent")
    errors: Mapped[list[ErrorEvent]] = relationship(back_populates="agent")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint("records_processed >= 0", name="ck_agent_runs_records_processed_nonnegative"),
        CheckConstraint("records_created >= 0", name="ck_agent_runs_records_created_nonnegative"),
        CheckConstraint("retry_count >= 0", name="ck_agent_runs_retry_count_nonnegative"),
        CheckConstraint("error_count >= 0", name="ck_agent_runs_error_count_nonnegative"),
        Index("ix_agent_runs_agent_status", "agent_id", "status"),
        Index("ix_agent_runs_created", "run_id"),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agents.agent_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    trigger_type: Mapped[TriggerType] = mapped_column(
        Enum(TriggerType, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str | None] = mapped_column(Text)

    agent: Mapped[Agent] = relationship(back_populates="runs")
    errors: Mapped[list[ErrorEvent]] = relationship(back_populates="run")


class ErrorEvent(Base):
    __tablename__ = "error_events"
    __table_args__ = (
        Index("ix_error_events_run_created", "run_id", "created_at"),
        Index("ix_error_events_agent_created", "agent_id", "created_at"),
    )

    error_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("agent_runs.run_id", ondelete="SET NULL"), index=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("agents.agent_id", ondelete="SET NULL"), index=True
    )
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[ErrorSeverity] = mapped_column(
        Enum(ErrorSeverity, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    run: Mapped[AgentRun | None] = relationship(back_populates="errors")
    agent: Mapped[Agent | None] = relationship(back_populates="errors")


class SourceObservation(Base):
    __tablename__ = "source_observations"
    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_source_observations_confidence_score_range",
        ),
        Index("ix_source_observations_source_captured", "source_id", "captured_at"),
        Index("ix_source_observations_run_captured", "run_id", "captured_at"),
        Index("ix_source_observations_product_status", "product_id", "extraction_status"),
    )

    observation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.source_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    captured_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    raw_text: Mapped[str | None] = mapped_column(Text)
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        default=EvidenceType.UNKNOWN,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float)
    buyer_id: Mapped[str | None] = mapped_column(String(64), index=True)
    requirement_id: Mapped[str | None] = mapped_column(String(64), index=True)
    product_id: Mapped[str | None] = mapped_column(String(64), index=True)
    company_name: Mapped[str | None] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(100), index=True)
    requirement_text: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(50))
    specifications: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False, default=dict)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    contact_phone: Mapped[str | None] = mapped_column(String(100))
    posted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    extractor_type: Mapped[str] = mapped_column(String(100), nullable=False)
    observation_metadata: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False, default=dict)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_entity_timestamp", "entity_type", "entity_id", "timestamp"),
        Index("ix_audit_events_actor_timestamp", "actor_type", "actor_id", "timestamp"),
    )

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
