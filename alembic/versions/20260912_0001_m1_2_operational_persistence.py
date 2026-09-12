"""m1.2 operational persistence

Revision ID: 20260912_0001
Revises:
Create Date: 2026-09-12 00:00:00.000000
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260912_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.Enum("active", "idle", "running", "degraded", "failed", "disabled", name="agentstatus", native_enum=False, length=32), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("capabilities", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("authority_level", sa.Enum("green", "yellow", "red", name="authoritylevel", native_enum=False, length=16), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_index(op.f("ix_agents_status"), "agents", ["status"], unique=False)
    op.create_index(op.f("ix_agents_type"), "agents", ["type"], unique=False)

    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("trigger_type", sa.Enum("manual", "scheduled", "event", "retry", "system", name="triggertype", native_enum=False, length=32), nullable=False),
        sa.Column("status", sa.Enum("queued", "running", "completed", "completed_with_warnings", "failed", "cancelled", name="runstatus", native_enum=False, length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.CheckConstraint("error_count >= 0", name="ck_agent_runs_error_count_nonnegative"),
        sa.CheckConstraint("records_created >= 0", name="ck_agent_runs_records_created_nonnegative"),
        sa.CheckConstraint("records_processed >= 0", name="ck_agent_runs_records_processed_nonnegative"),
        sa.CheckConstraint("retry_count >= 0", name="ck_agent_runs_retry_count_nonnegative"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_agent_runs_agent_status", "agent_runs", ["agent_id", "status"], unique=False)
    op.create_index("ix_agent_runs_created", "agent_runs", ["run_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_agent_id"), "agent_runs", ["agent_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_status"), "agent_runs", ["status"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("before_state", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("after_state", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_audit_events_actor_timestamp", "audit_events", ["actor_type", "actor_id", "timestamp"], unique=False)
    op.create_index("ix_audit_events_entity_timestamp", "audit_events", ["entity_type", "entity_id", "timestamp"], unique=False)

    op.create_table(
        "error_events",
        sa.Column("error_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.Enum("info", "warning", "error", "critical", name="errorseverity", native_enum=False, length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("error_id"),
    )
    op.create_index("ix_error_events_agent_created", "error_events", ["agent_id", "created_at"], unique=False)
    op.create_index("ix_error_events_run_created", "error_events", ["run_id", "created_at"], unique=False)
    op.create_index(op.f("ix_error_events_agent_id"), "error_events", ["agent_id"], unique=False)
    op.create_index(op.f("ix_error_events_run_id"), "error_events", ["run_id"], unique=False)

    agents_table = sa.table(
        "agents",
        sa.column("agent_id", sa.String),
        sa.column("name", sa.String),
        sa.column("type", sa.String),
        sa.column("status", sa.String),
        sa.column("version", sa.String),
        sa.column("capabilities", sa.JSON),
        sa.column("authority_level", sa.String),
        sa.column("last_heartbeat_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    seeded_at = datetime(2026, 9, 12, tzinfo=UTC)
    op.bulk_insert(
        agents_table,
        [
            {
                "agent_id": "AGT-BUYER-DISCOVERY-001",
                "name": "Buyer Discovery",
                "type": "buyer_discovery",
                "status": "active",
                "version": "0.1.0",
                "capabilities": [],
                "authority_level": "green",
                "last_heartbeat_at": None,
                "created_at": seeded_at,
                "updated_at": seeded_at,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_error_events_run_id"), table_name="error_events")
    op.drop_index(op.f("ix_error_events_agent_id"), table_name="error_events")
    op.drop_index("ix_error_events_run_created", table_name="error_events")
    op.drop_index("ix_error_events_agent_created", table_name="error_events")
    op.drop_table("error_events")

    op.drop_index("ix_audit_events_entity_timestamp", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_timestamp", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index(op.f("ix_agent_runs_status"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_agent_id"), table_name="agent_runs")
    op.drop_index("ix_agent_runs_created", table_name="agent_runs")
    op.drop_index("ix_agent_runs_agent_status", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index(op.f("ix_agents_type"), table_name="agents")
    op.drop_index(op.f("ix_agents_status"), table_name="agents")
    op.drop_table("agents")
