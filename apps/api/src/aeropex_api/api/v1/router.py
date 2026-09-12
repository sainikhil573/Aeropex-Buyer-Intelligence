"""API v1 router."""

from typing import Annotated

from aeropex_contracts.enums import AgentStatus, RunStatus
from aeropex_workers.celery_app import operational_test_run_task
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from aeropex_api.api.v1.schemas import (
    AgentResponse,
    AgentRunResponse,
    ErrorEventResponse,
    OverviewResponse,
    RunCreateRequest,
    RunCreateResponse,
)
from aeropex_api.db.models import Agent, AgentRun, ErrorEvent
from aeropex_api.db.session import get_db_session
from aeropex_api.services.run_lifecycle import AgentNotFoundError, AgentRunService

api_router = APIRouter()
SessionDep = Annotated[Session, Depends(get_db_session)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]
AgentIdQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


@api_router.get("/health", tags=["system"])
async def versioned_health() -> dict[str, str]:
    return {"status": "healthy", "service": "aeropex-api", "api_version": "v1"}


@api_router.get("/agents", response_model=list[AgentResponse], tags=["agents"])
def list_agents(session: SessionDep) -> list[Agent]:
    return session.query(Agent).order_by(Agent.agent_id).all()


@api_router.get("/agents/{agent_id}", response_model=AgentResponse, tags=["agents"])
def get_agent(agent_id: str, session: SessionDep) -> Agent:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@api_router.get("/overview", response_model=OverviewResponse, tags=["system"])
def get_overview(session: SessionDep) -> OverviewResponse:
    total_agents = session.query(Agent).count()
    running_agents = session.query(Agent).filter(Agent.status == AgentStatus.RUNNING).count()
    recent_runs = session.query(AgentRun).count()
    failed_runs = session.query(AgentRun).filter(AgentRun.status == RunStatus.FAILED).count()
    platform_status = "healthy"
    if failed_runs:
        platform_status = "degraded"
    return OverviewResponse(
        platform_status=platform_status,
        total_agents=total_agents,
        running_agents=running_agents,
        recent_runs=recent_runs,
        failed_runs=failed_runs,
    )


@api_router.get("/runs", response_model=list[AgentRunResponse], tags=["runs"])
def list_runs(
    session: SessionDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    agent_id: AgentIdQuery = None,
) -> list:
    return AgentRunService(session).list_runs(limit=limit, offset=offset, agent_id=agent_id)


@api_router.get("/runs/{run_id}", response_model=AgentRunResponse, tags=["runs"])
def get_run(run_id: str, session: SessionDep) -> object:
    run = AgentRunService(session).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@api_router.get("/errors", response_model=list[ErrorEventResponse], tags=["errors"])
def list_errors(
    session: SessionDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> list[ErrorEvent]:
    return (
        session.query(ErrorEvent)
        .order_by(ErrorEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@api_router.post(
    "/runs",
    response_model=RunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["runs"],
)
def create_run(payload: RunCreateRequest, session: SessionDep) -> RunCreateResponse:
    service = AgentRunService(session)
    try:
        run = service.create_run(
            agent_id=payload.agent_id,
            trigger_type=payload.trigger_type,
            run_id=payload.run_id,
            summary="Queued safe operational test run.",
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found") from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run already exists") from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Operational database unavailable",
        ) from exc

    task = operational_test_run_task.delay(run.run_id, simulate_failure=payload.simulate_failure)
    return RunCreateResponse.model_validate(run, from_attributes=True).model_copy(
        update={"task_id": task.id}
    )
