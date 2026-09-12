"""Agent run lifecycle service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from aeropex_contracts.enums import ErrorSeverity, RunStatus, TriggerType
from sqlalchemy.orm import Session

from aeropex_api.db.models import Agent, AgentRun, AuditEvent, ErrorEvent


class RunLifecycleError(ValueError):
    """Raised when a run lifecycle transition is invalid."""


class AgentNotFoundError(ValueError):
    """Raised when an agent does not exist."""


TERMINAL_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.COMPLETED_WITH_WARNINGS,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}

ALLOWED_TRANSITIONS = {
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {
        RunStatus.COMPLETED,
        RunStatus.COMPLETED_WITH_WARNINGS,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def make_id(prefix: str) -> str:
    return f"{prefix}-{utc_now():%Y%m%d}-{uuid4().hex[:12].upper()}"


class AgentRunService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(
        self,
        *,
        agent_id: str,
        trigger_type: TriggerType = TriggerType.MANUAL,
        run_id: str | None = None,
        summary: str | None = None,
    ) -> AgentRun:
        if self.session.get(Agent, agent_id) is None:
            raise AgentNotFoundError(f"Agent not found: {agent_id}")

        now = utc_now()
        run = AgentRun(
            run_id=run_id or make_id("RUN"),
            agent_id=agent_id,
            trigger_type=trigger_type,
            status=RunStatus.QUEUED,
            started_at=None,
            finished_at=None,
            records_processed=0,
            records_created=0,
            retry_count=0,
            error_count=0,
            summary=summary,
        )
        self.session.add(run)
        self._add_audit(
            actor_type="system",
            actor_id="aeropex-api",
            action="created_agent_run",
            entity_type="agent_run",
            entity_id=run.run_id,
            before_state=None,
            after_state={"status": RunStatus.QUEUED.value},
            timestamp=now,
        )
        self.session.commit()
        self.session.refresh(run)
        return run

    def mark_running(self, run_id: str) -> AgentRun:
        return self._transition(run_id, RunStatus.RUNNING, started_at=utc_now())

    def mark_completed(
        self,
        run_id: str,
        *,
        records_processed: int = 0,
        records_created: int = 0,
        summary: str | None = None,
        completed_with_warnings: bool = False,
    ) -> AgentRun:
        status = RunStatus.COMPLETED_WITH_WARNINGS if completed_with_warnings else RunStatus.COMPLETED
        return self._transition(
            run_id,
            status,
            finished_at=utc_now(),
            records_processed=records_processed,
            records_created=records_created,
            summary=summary,
        )

    def mark_failed(
        self,
        run_id: str,
        *,
        error_type: str,
        message: str,
        retryable: bool = False,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
    ) -> AgentRun:
        run = self._transition(run_id, RunStatus.FAILED, finished_at=utc_now())
        self.create_error_event(
            run_id=run.run_id,
            agent_id=run.agent_id,
            error_type=error_type,
            severity=severity,
            message=message,
            retryable=retryable,
            resolved=False,
            commit=False,
        )
        run.error_count += 1
        self.session.commit()
        self.session.refresh(run)
        return run

    def mark_cancelled(self, run_id: str, *, summary: str | None = None) -> AgentRun:
        return self._transition(run_id, RunStatus.CANCELLED, finished_at=utc_now(), summary=summary)

    def get_run(self, run_id: str) -> AgentRun | None:
        return self.session.get(AgentRun, run_id)

    def list_runs(self, *, limit: int = 50, offset: int = 0) -> list[AgentRun]:
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        return (
            self.session.query(AgentRun)
            .order_by(AgentRun.run_id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create_error_event(
        self,
        *,
        error_type: str,
        severity: ErrorSeverity,
        message: str,
        retryable: bool,
        resolved: bool,
        run_id: str | None = None,
        agent_id: str | None = None,
        commit: bool = True,
    ) -> ErrorEvent:
        event = ErrorEvent(
            error_id=make_id("ERR"),
            run_id=run_id,
            agent_id=agent_id,
            error_type=error_type,
            severity=severity,
            message=message,
            retryable=retryable,
            resolved=resolved,
            created_at=utc_now(),
        )
        self.session.add(event)
        if commit:
            self.session.commit()
            self.session.refresh(event)
        return event

    def _transition(self, run_id: str, new_status: RunStatus, **updates: object) -> AgentRun:
        run = self.session.get(AgentRun, run_id)
        if run is None:
            raise KeyError(run_id)

        old_status = run.status
        if old_status in TERMINAL_STATUSES:
            raise RunLifecycleError(f"Run {run_id} is terminal: {old_status.value}")
        if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
            raise RunLifecycleError(f"Invalid run transition: {old_status.value} -> {new_status.value}")

        before_state = {"status": old_status.value}
        run.status = new_status
        for key, value in updates.items():
            if value is not None or key in {"summary"}:
                setattr(run, key, value)

        self._validate_counters(run)
        self._add_audit(
            actor_type="system",
            actor_id="run_lifecycle",
            action="updated_agent_run_status",
            entity_type="agent_run",
            entity_id=run.run_id,
            before_state=before_state,
            after_state={"status": new_status.value},
            timestamp=utc_now(),
        )
        self.session.commit()
        self.session.refresh(run)
        return run

    def _add_audit(
        self,
        *,
        actor_type: str,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before_state: dict[str, object] | None,
        after_state: dict[str, object] | None,
        timestamp: datetime,
    ) -> AuditEvent:
        event = AuditEvent(
            audit_id=make_id("AUD"),
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            timestamp=timestamp,
        )
        self.session.add(event)
        return event

    @staticmethod
    def _validate_counters(run: AgentRun) -> None:
        counters = (
            run.records_processed,
            run.records_created,
            run.retry_count,
            run.error_count,
        )
        if any(counter < 0 for counter in counters):
            raise ValueError("run counters must be non-negative")
