"""m2.1 product and source configuration

Revision ID: 20260912_0002
Revises: 20260912_0001
Create Date: 2026-09-12 00:00:00.000000
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260912_0002"
down_revision = "20260912_0001"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("aliases", json_type, nullable=False),
        sa.Column("variants", json_type, nullable=False),
        sa.Column("hs_codes", json_type, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("priority >= 0", name="ck_products_priority_nonnegative"),
        sa.PrimaryKeyConstraint("product_id"),
    )
    op.create_index("ix_products_category_active", "products", ["category", "active"], unique=False)
    op.create_index(op.f("ix_products_active"), "products", ["active"], unique=False)
    op.create_index(op.f("ix_products_category"), "products", ["category"], unique=False)
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)

    op.create_table(
        "sources",
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("access_method", sa.Enum("api", "http", "browser", "manual", name="sourceaccessmethod", native_enum=False, length=32), nullable=False),
        sa.Column("approval_status", sa.Enum("candidate", "approved", "rejected", name="sourceapprovalstatus", native_enum=False, length=32), nullable=False),
        sa.Column("operational_status", sa.Enum("active", "degraded", "disabled", "unavailable", name="sourceoperationalstatus", native_enum=False, length=32), nullable=False),
        sa.Column("reliability_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("product_relevance", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("reliability_score >= 0 AND reliability_score <= 1", name="ck_sources_reliability_score_range"),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_index("ix_sources_approval_operational", "sources", ["approval_status", "operational_status"], unique=False)
    op.create_index(op.f("ix_sources_approval_status"), "sources", ["approval_status"], unique=False)
    op.create_index(op.f("ix_sources_country"), "sources", ["country"], unique=False)
    op.create_index(op.f("ix_sources_domain"), "sources", ["domain"], unique=False)
    op.create_index(op.f("ix_sources_name"), "sources", ["name"], unique=False)
    op.create_index(op.f("ix_sources_operational_status"), "sources", ["operational_status"], unique=False)
    op.create_index(op.f("ix_sources_source_type"), "sources", ["source_type"], unique=False)

    seeded_at = datetime(2026, 9, 12, tzinfo=UTC)
    products_table = sa.table(
        "products",
        sa.column("product_id", sa.String),
        sa.column("category", sa.String),
        sa.column("name", sa.String),
        sa.column("aliases", sa.JSON),
        sa.column("variants", sa.JSON),
        sa.column("hs_codes", sa.JSON),
        sa.column("priority", sa.Integer),
        sa.column("active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        products_table,
        [
            {"product_id": "PRD-RED-CHILLI", "category": "Spices", "name": "Red Chilli", "aliases": [], "variants": [], "hs_codes": [], "priority": 10, "active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"product_id": "PRD-TURMERIC", "category": "Spices", "name": "Turmeric", "aliases": [], "variants": [], "hs_codes": [], "priority": 20, "active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"product_id": "PRD-BLACK-PEPPER", "category": "Spices", "name": "Black Pepper", "aliases": [], "variants": [], "hs_codes": [], "priority": 30, "active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"product_id": "PRD-CUMIN", "category": "Spices", "name": "Cumin", "aliases": [], "variants": [], "hs_codes": [], "priority": 40, "active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"product_id": "PRD-CORIANDER", "category": "Spices", "name": "Coriander", "aliases": [], "variants": [], "hs_codes": [], "priority": 50, "active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"product_id": "PRD-CARDAMOM", "category": "Spices", "name": "Cardamom", "aliases": [], "variants": [], "hs_codes": [], "priority": 60, "active": True, "created_at": seeded_at, "updated_at": seeded_at},
        ],
    )

    sources_table = sa.table(
        "sources",
        sa.column("source_id", sa.String),
        sa.column("name", sa.String),
        sa.column("domain", sa.String),
        sa.column("country", sa.String),
        sa.column("source_type", sa.String),
        sa.column("access_method", sa.String),
        sa.column("approval_status", sa.String),
        sa.column("operational_status", sa.String),
        sa.column("reliability_score", sa.Numeric),
        sa.column("last_checked_at", sa.DateTime(timezone=True)),
        sa.column("notes", sa.Text),
        sa.column("product_relevance", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        sources_table,
        [
            {"source_id": "SRC-TRADE-PORTAL-CANDIDATE", "name": "Trade Portal Candidate", "domain": "example-trade.invalid", "country": None, "source_type": "trade_portal", "access_method": "http", "approval_status": "candidate", "operational_status": "active", "reliability_score": None, "last_checked_at": None, "notes": "Placeholder registry candidate; no connector implemented.", "product_relevance": [], "created_at": seeded_at, "updated_at": seeded_at},
            {"source_id": "SRC-MANUAL-RESEARCH-CANDIDATE", "name": "Manual Research Candidate", "domain": None, "country": None, "source_type": "manual_research", "access_method": "manual", "approval_status": "candidate", "operational_status": "active", "reliability_score": None, "last_checked_at": None, "notes": "Placeholder for governed source intake.", "product_relevance": [], "created_at": seeded_at, "updated_at": seeded_at},
            {"source_id": "SRC-PUBLIC-DIRECTORY-CANDIDATE", "name": "Public Directory Candidate", "domain": "example-directory.invalid", "country": None, "source_type": "directory", "access_method": "http", "approval_status": "candidate", "operational_status": "active", "reliability_score": None, "last_checked_at": None, "notes": "Candidate registry metadata only.", "product_relevance": [], "created_at": seeded_at, "updated_at": seeded_at},
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sources_source_type"), table_name="sources")
    op.drop_index(op.f("ix_sources_operational_status"), table_name="sources")
    op.drop_index(op.f("ix_sources_name"), table_name="sources")
    op.drop_index(op.f("ix_sources_domain"), table_name="sources")
    op.drop_index(op.f("ix_sources_country"), table_name="sources")
    op.drop_index(op.f("ix_sources_approval_status"), table_name="sources")
    op.drop_index("ix_sources_approval_operational", table_name="sources")
    op.drop_table("sources")

    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_index(op.f("ix_products_category"), table_name="products")
    op.drop_index(op.f("ix_products_active"), table_name="products")
    op.drop_index("ix_products_category_active", table_name="products")
    op.drop_table("products")
