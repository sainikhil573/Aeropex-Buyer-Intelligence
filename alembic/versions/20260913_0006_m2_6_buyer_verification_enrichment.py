"""m2.6 buyer verification and enrichment

Revision ID: 20260913_0006
Revises: 20260913_0005
Create Date: 2026-09-13 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260913_0006"
down_revision = "20260913_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    verification_status = sa.Enum(
        "unverified",
        "pending",
        "partially_verified",
        "verified",
        "rejected",
        name="verificationstatus",
        native_enum=False,
        length=32,
    )
    op.create_table(
        "verification_results",
        sa.Column("verification_id", sa.String(length=64), nullable=False),
        sa.Column("buyer_id", sa.String(length=64), nullable=False),
        sa.Column("status", verification_status, nullable=False),
        sa.Column(
            "verification_type",
            sa.Enum("company", "contact", "requirement", "manual", name="verificationtype", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_verification_results_confidence_score_range",
        ),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.buyer_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("verification_id"),
    )
    op.create_index(op.f("ix_verification_results_buyer_id"), "verification_results", ["buyer_id"], unique=False)
    op.create_index("ix_verification_results_buyer_status", "verification_results", ["buyer_id", "status"], unique=False)
    op.create_index(op.f("ix_verification_results_status"), "verification_results", ["status"], unique=False)
    op.create_index(
        op.f("ix_verification_results_verification_type"),
        "verification_results",
        ["verification_type"],
        unique=False,
    )

    op.create_table(
        "verification_evidence",
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("verification_id", sa.String(length=64), nullable=False),
        sa.Column("buyer_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "claim_type",
            sa.Enum(
                "company_exists",
                "website_association",
                "domain_association",
                "contact_association",
                "phone_association",
                "email_association",
                "business_relevance",
                "address_association",
                "other",
                name="verificationclaimtype",
                native_enum=False,
                length=64,
            ),
            nullable=False,
        ),
        sa.Column("claim_value", sa.Text(), nullable=True),
        sa.Column("supports_claim", sa.Boolean(), nullable=True),
        sa.Column("evidence_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.buyer_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["verification_id"], ["verification_results.verification_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("evidence_id"),
    )
    op.create_index(op.f("ix_verification_evidence_buyer_id"), "verification_evidence", ["buyer_id"], unique=False)
    op.create_index(op.f("ix_verification_evidence_claim_type"), "verification_evidence", ["claim_type"], unique=False)
    op.create_index(
        "ix_verification_evidence_verification_claim",
        "verification_evidence",
        ["verification_id", "claim_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_evidence_verification_id"),
        "verification_evidence",
        ["verification_id"],
        unique=False,
    )

    op.create_table(
        "contacts",
        sa.Column("contact_id", sa.String(length=64), nullable=False),
        sa.Column("buyer_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("normalized_email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("normalized_phone", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column(
            "contact_type",
            sa.Enum("general", "procurement", "sales", "owner", "operations", "other", name="contacttype", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.Column("source_observation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.buyer_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("contact_id"),
    )
    op.create_index(op.f("ix_contacts_buyer_id"), "contacts", ["buyer_id"], unique=False)
    op.create_index("ix_contacts_buyer_email", "contacts", ["buyer_id", "normalized_email"], unique=False)
    op.create_index("ix_contacts_buyer_phone", "contacts", ["buyer_id", "normalized_phone"], unique=False)
    op.create_index("ix_contacts_buyer_status", "contacts", ["buyer_id", "verification_status"], unique=False)
    op.create_index(op.f("ix_contacts_contact_type"), "contacts", ["contact_type"], unique=False)
    op.create_index(op.f("ix_contacts_normalized_email"), "contacts", ["normalized_email"], unique=False)
    op.create_index(op.f("ix_contacts_normalized_phone"), "contacts", ["normalized_phone"], unique=False)
    op.create_index(op.f("ix_contacts_source_observation_id"), "contacts", ["source_observation_id"], unique=False)
    op.create_index(op.f("ix_contacts_verification_status"), "contacts", ["verification_status"], unique=False)

    op.create_table(
        "enrichment_results",
        sa.Column("enrichment_id", sa.String(length=64), nullable=False),
        sa.Column("buyer_id", sa.String(length=64), nullable=False),
        sa.Column("contact_id", sa.String(length=64), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("discovered", "accepted", "rejected", name="enrichmentstatus", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.buyer_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.contact_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("enrichment_id"),
    )
    op.create_index(op.f("ix_enrichment_results_buyer_id"), "enrichment_results", ["buyer_id"], unique=False)
    op.create_index("ix_enrichment_results_buyer_field", "enrichment_results", ["buyer_id", "field_name"], unique=False)
    op.create_index("ix_enrichment_results_buyer_status", "enrichment_results", ["buyer_id", "status"], unique=False)
    op.create_index(op.f("ix_enrichment_results_contact_id"), "enrichment_results", ["contact_id"], unique=False)
    op.create_index(op.f("ix_enrichment_results_status"), "enrichment_results", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_enrichment_results_status"), table_name="enrichment_results")
    op.drop_index(op.f("ix_enrichment_results_contact_id"), table_name="enrichment_results")
    op.drop_index("ix_enrichment_results_buyer_status", table_name="enrichment_results")
    op.drop_index("ix_enrichment_results_buyer_field", table_name="enrichment_results")
    op.drop_index(op.f("ix_enrichment_results_buyer_id"), table_name="enrichment_results")
    op.drop_table("enrichment_results")
    op.drop_index(op.f("ix_contacts_verification_status"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_source_observation_id"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_normalized_phone"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_normalized_email"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_contact_type"), table_name="contacts")
    op.drop_index("ix_contacts_buyer_status", table_name="contacts")
    op.drop_index("ix_contacts_buyer_phone", table_name="contacts")
    op.drop_index("ix_contacts_buyer_email", table_name="contacts")
    op.drop_index(op.f("ix_contacts_buyer_id"), table_name="contacts")
    op.drop_table("contacts")
    op.drop_index(op.f("ix_verification_evidence_verification_id"), table_name="verification_evidence")
    op.drop_index("ix_verification_evidence_verification_claim", table_name="verification_evidence")
    op.drop_index(op.f("ix_verification_evidence_claim_type"), table_name="verification_evidence")
    op.drop_index(op.f("ix_verification_evidence_buyer_id"), table_name="verification_evidence")
    op.drop_table("verification_evidence")
    op.drop_index(op.f("ix_verification_results_verification_type"), table_name="verification_results")
    op.drop_index(op.f("ix_verification_results_status"), table_name="verification_results")
    op.drop_index("ix_verification_results_buyer_status", table_name="verification_results")
    op.drop_index(op.f("ix_verification_results_buyer_id"), table_name="verification_results")
    op.drop_table("verification_results")
