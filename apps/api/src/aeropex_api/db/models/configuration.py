"""Platform-owned product and source configuration models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from aeropex_contracts.enums import (
    SourceAccessMethod,
    SourceApprovalStatus,
    SourceOperationalStatus,
)
from sqlalchemy import Boolean, CheckConstraint, Enum, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aeropex_api.db.base import Base
from aeropex_api.db.models.operational import UTCDateTime, enum_values, json_type


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("priority >= 0", name="ck_products_priority_nonnegative"),
        Index("ix_products_category_active", "category", "active"),
    )

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(json_type, nullable=False, default=list)
    variants: Mapped[list[str]] = mapped_column(json_type, nullable=False, default=list)
    hs_codes: Mapped[list[str]] = mapped_column(json_type, nullable=False, default=list)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("reliability_score >= 0 AND reliability_score <= 1", name="ck_sources_reliability_score_range"),
        Index("ix_sources_approval_operational", "approval_status", "operational_status"),
    )

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(2), index=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    access_method: Mapped[SourceAccessMethod] = mapped_column(
        Enum(SourceAccessMethod, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
    )
    approval_status: Mapped[SourceApprovalStatus] = mapped_column(
        Enum(SourceApprovalStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    operational_status: Mapped[SourceOperationalStatus] = mapped_column(
        Enum(SourceOperationalStatus, values_callable=enum_values, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    reliability_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    last_checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    product_relevance: Mapped[list[str]] = mapped_column(json_type, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
