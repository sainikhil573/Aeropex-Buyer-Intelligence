"""m2.5 canonical buyer entity resolution

Revision ID: 20260913_0005
Revises: 20260912_0004
Create Date: 2026-09-13 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260913_0005"
down_revision = "20260912_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "buyers",
        sa.Column("buyer_id", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_company_name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column("primary_domain", sa.String(length=255), nullable=True),
        sa.Column("company_type", sa.String(length=100), nullable=True),
        sa.Column(
            "verification_status",
            sa.Enum(
                "unverified",
                "pending",
                "partially_verified",
                "verified",
                "rejected",
                name="verificationstatus",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_buyers_confidence_score_range",
        ),
        sa.PrimaryKeyConstraint("buyer_id"),
    )
    op.create_index(op.f("ix_buyers_country"), "buyers", ["country"], unique=False)
    op.create_index(
        "ix_buyers_normalized_country",
        "buyers",
        ["normalized_company_name", "country"],
        unique=False,
    )
    op.create_index(
        op.f("ix_buyers_normalized_company_name"),
        "buyers",
        ["normalized_company_name"],
        unique=False,
    )
    op.create_index(op.f("ix_buyers_primary_domain"), "buyers", ["primary_domain"], unique=False)
    op.create_index(
        op.f("ix_buyers_verification_status"),
        "buyers",
        ["verification_status"],
        unique=False,
    )

    op.create_table(
        "buyer_requirements",
        sa.Column("requirement_id", sa.String(length=64), nullable=False),
        sa.Column("buyer_id", sa.String(length=64), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=True),
        sa.Column("requirement_text", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("specifications", sa.JSON(), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "closed", name="buyerrequirementstatus", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_buyer_requirements_quantity_nonnegative"),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.buyer_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("requirement_id"),
    )
    op.create_index(op.f("ix_buyer_requirements_buyer_id"), "buyer_requirements", ["buyer_id"], unique=False)
    op.create_index(
        "ix_buyer_requirements_buyer_status",
        "buyer_requirements",
        ["buyer_id", "status"],
        unique=False,
    )
    op.create_index(op.f("ix_buyer_requirements_product_id"), "buyer_requirements", ["product_id"], unique=False)
    op.create_index(op.f("ix_buyer_requirements_status"), "buyer_requirements", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_buyer_requirements_status"), table_name="buyer_requirements")
    op.drop_index(op.f("ix_buyer_requirements_product_id"), table_name="buyer_requirements")
    op.drop_index("ix_buyer_requirements_buyer_status", table_name="buyer_requirements")
    op.drop_index(op.f("ix_buyer_requirements_buyer_id"), table_name="buyer_requirements")
    op.drop_table("buyer_requirements")
    op.drop_index(op.f("ix_buyers_verification_status"), table_name="buyers")
    op.drop_index(op.f("ix_buyers_primary_domain"), table_name="buyers")
    op.drop_index(op.f("ix_buyers_normalized_company_name"), table_name="buyers")
    op.drop_index("ix_buyers_normalized_country", table_name="buyers")
    op.drop_index(op.f("ix_buyers_country"), table_name="buyers")
    op.drop_table("buyers")
