from datetime import UTC

import pytest
from aeropex_api.db.base import Base, import_models
from aeropex_api.db.models import Agent, AgentRun, AuditEvent, ErrorEvent
from aeropex_api.services.bootstrap import BUYER_DISCOVERY_AGENT_ID, bootstrap_initial_agents
from aeropex_api.services.run_lifecycle import AgentRunService, RunLifecycleError
from aeropex_contracts.enums import AgentStatus, ErrorSeverity, RunStatus
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def session() -> Session:
    import_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as db_session:
        bootstrap_initial_agents(db_session)
        yield db_session


def test_agent_persistence_model_behavior(session: Session) -> None:
    agent = session.get(Agent, BUYER_DISCOVERY_AGENT_ID)

    assert agent is not None
    assert agent.status == AgentStatus.ACTIVE
    assert agent.name == "Buyer Discovery"


def test_agent_run_persistence_and_queued_creation(session: Session) -> None:
    run = AgentRunService(session).create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)

    assert run.status == RunStatus.QUEUED
    assert run.started_at is None
    assert session.get(AgentRun, run.run_id) is not None


def test_duplicate_run_id_is_rejected(session: Session) -> None:
    service = AgentRunService(session)
    service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID, run_id="RUN-DUPLICATE")

    with pytest.raises(IntegrityError):
        service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID, run_id="RUN-DUPLICATE")


def test_queued_to_running_transition(session: Session) -> None:
    service = AgentRunService(session)
    run = service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)

    running = service.mark_running(run.run_id)

    assert running.status == RunStatus.RUNNING
    assert running.started_at is not None
    assert running.started_at.tzinfo is not None


def test_running_to_completed_transition_and_timestamp(session: Session) -> None:
    service = AgentRunService(session)
    run = service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)
    service.mark_running(run.run_id)

    completed = service.mark_completed(run.run_id, records_processed=2, records_created=1)

    assert completed.status == RunStatus.COMPLETED
    assert completed.finished_at is not None
    assert completed.finished_at.tzinfo is not None
    assert completed.records_processed == 2
    assert completed.records_created == 1


def test_running_to_failed_transition_timestamp_and_error_event(session: Session) -> None:
    service = AgentRunService(session)
    run = service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)
    service.mark_running(run.run_id)

    failed = service.mark_failed(
        run.run_id,
        error_type="simulated_failure",
        severity=ErrorSeverity.ERROR,
        message="Simulated failure",
    )

    assert failed.status == RunStatus.FAILED
    assert failed.finished_at is not None
    assert failed.error_count == 1
    event = session.query(ErrorEvent).filter_by(run_id=run.run_id).one()
    assert event.message == "Simulated failure"
    assert event.agent_id == BUYER_DISCOVERY_AGENT_ID


def test_invalid_transition_rejected(session: Session) -> None:
    service = AgentRunService(session)
    run = service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)

    with pytest.raises(RunLifecycleError):
        service.mark_completed(run.run_id)


def test_terminal_state_protection(session: Session) -> None:
    service = AgentRunService(session)
    run = service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)
    service.mark_running(run.run_id)
    service.mark_completed(run.run_id)

    with pytest.raises(RunLifecycleError):
        service.mark_running(run.run_id)


def test_non_negative_counter_enforcement(session: Session) -> None:
    service = AgentRunService(session)
    run = service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)
    service.mark_running(run.run_id)

    with pytest.raises(ValueError):
        service.mark_completed(run.run_id, records_processed=-1)


def test_audit_events_created_for_lifecycle_transitions(session: Session) -> None:
    service = AgentRunService(session)
    run = service.create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)
    service.mark_running(run.run_id)

    events = session.query(AuditEvent).filter_by(entity_id=run.run_id).all()

    assert [event.after_state["status"] for event in events] == ["queued", "running"]
    assert all(event.timestamp.tzinfo is not None for event in events)


def test_error_event_can_exist_without_run_or_agent(session: Session) -> None:
    event = AgentRunService(session).create_error_event(
        error_type="platform_failure",
        severity=ErrorSeverity.CRITICAL,
        message="Platform-level failure",
        retryable=False,
        resolved=False,
    )

    assert event.run_id is None
    assert event.agent_id is None
    assert event.created_at.tzinfo is UTC


def test_safe_celery_task_tracks_failed_run(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from aeropex_workers import celery_app as worker_module

    session_factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr(worker_module, "create_session_factory", lambda: session_factory)
    worker_module.celery_app.conf.task_always_eager = True
    worker_module.celery_app.conf.task_eager_propagates = True

    run = AgentRunService(session).create_run(agent_id=BUYER_DISCOVERY_AGENT_ID)

    with pytest.raises(RuntimeError):
        worker_module.operational_test_run_task.apply(
            args=(run.run_id,),
            kwargs={"simulate_failure": True},
        ).get()

    session.expire_all()
    failed_run = session.get(AgentRun, run.run_id)
    assert failed_run.status == RunStatus.FAILED
    assert session.query(ErrorEvent).filter_by(run_id=run.run_id).count() == 1
