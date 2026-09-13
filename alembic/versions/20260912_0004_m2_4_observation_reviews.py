"""m2.4 observation review workflow

Revision ID: 20260912_0004
Revises: 20260912_0003
Create Date: 2026-09-12 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260912_0004"
down_revision = "20260912_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "observation_reviews",
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("observation_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "unreviewed",
                "needs_review",
                "accepted",
                "rejected",
                name="observationreviewstatus",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["source_observations.observation_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("review_id"),
        sa.UniqueConstraint("observation_id"),
    )
    op.create_index(
        op.f("ix_observation_reviews_observation_id"),
        "observation_reviews",
        ["observation_id"],
        unique=True,
    )
    op.create_index(op.f("ix_observation_reviews_status"), "observation_reviews", ["status"], unique=False)
    op.create_index(
        "ix_observation_reviews_status_updated",
        "observation_reviews",
        ["status", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_observation_reviews_status_updated", table_name="observation_reviews")
    op.drop_index(op.f("ix_observation_reviews_status"), table_name="observation_reviews")
    op.drop_index(op.f("ix_observation_reviews_observation_id"), table_name="observation_reviews")
    op.drop_table("observation_reviews")
