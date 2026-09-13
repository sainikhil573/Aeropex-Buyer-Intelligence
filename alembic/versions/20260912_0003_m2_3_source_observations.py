"""m2.3 source observations and extraction evidence

Revision ID: 20260912_0003
Revises: 20260912_0002
Create Date: 2026-09-12 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260912_0003"
down_revision = "20260912_0002"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "source_observations",
        sa.Column("observation_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column(
            "evidence_type",
            sa.Enum(
                "page_text",
                "listing",
                "directory_entry",
                "api_record",
                "manual_entry",
                "unknown",
                name="evidencetype",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("buyer_id", sa.String(length=64), nullable=True),
        sa.Column("requirement_id", sa.String(length=64), nullable=True),
        sa.Column("product_id", sa.String(length=64), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("requirement_text", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("specifications", json_type, nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("contact_phone", sa.String(length=100), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "extraction_status",
            sa.Enum(
                "success",
                "partial",
                "unstructured",
                "failed",
                name="extractionstatus",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("extractor_type", sa.String(length=100), nullable=False),
        sa.Column("observation_metadata", json_type, nullable=False),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_source_observations_confidence_score_range",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.source_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("observation_id"),
    )
    op.create_index(op.f("ix_source_observations_captured_at"), "source_observations", ["captured_at"], unique=False)
    op.create_index(op.f("ix_source_observations_buyer_id"), "source_observations", ["buyer_id"], unique=False)
    op.create_index(op.f("ix_source_observations_company_name"), "source_observations", ["company_name"], unique=False)
    op.create_index(op.f("ix_source_observations_country"), "source_observations", ["country"], unique=False)
    op.create_index(
        op.f("ix_source_observations_extraction_status"),
        "source_observations",
        ["extraction_status"],
        unique=False,
    )
    op.create_index(op.f("ix_source_observations_product_id"), "source_observations", ["product_id"], unique=False)
    op.create_index(
        "ix_source_observations_product_status",
        "source_observations",
        ["product_id", "extraction_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_observations_requirement_id"),
        "source_observations",
        ["requirement_id"],
        unique=False,
    )
    op.create_index(op.f("ix_source_observations_run_id"), "source_observations", ["run_id"], unique=False)
    op.create_index(
        "ix_source_observations_run_captured",
        "source_observations",
        ["run_id", "captured_at"],
        unique=False,
    )
    op.create_index(op.f("ix_source_observations_source_id"), "source_observations", ["source_id"], unique=False)
    op.create_index(
        "ix_source_observations_source_captured",
        "source_observations",
        ["source_id", "captured_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_source_observations_source_captured", table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_source_id"), table_name="source_observations")
    op.drop_index("ix_source_observations_run_captured", table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_run_id"), table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_requirement_id"), table_name="source_observations")
    op.drop_index("ix_source_observations_product_status", table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_product_id"), table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_extraction_status"), table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_country"), table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_company_name"), table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_buyer_id"), table_name="source_observations")
    op.drop_index(op.f("ix_source_observations_captured_at"), table_name="source_observations")
    op.drop_table("source_observations")
