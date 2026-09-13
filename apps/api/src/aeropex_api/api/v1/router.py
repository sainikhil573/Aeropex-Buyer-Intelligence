"""API v1 router."""

from typing import Annotated

from aeropex_contracts.enums import (
    AgentStatus,
    ConnectorStatus,
    ExtractionStatus,
    RunStatus,
    SourceApprovalStatus,
    SourceOperationalStatus,
)
from aeropex_contracts.models import (
    ConnectorResult,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    SourceCreate,
    SourceRead,
    SourceUpdate,
)
from aeropex_workers.celery_app import operational_test_run_task
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from aeropex_api.api.v1.schemas import (
    AgentResponse,
    AgentRunResponse,
    ConnectorResultResponse,
    ConnectorTestRequest,
    ErrorEventResponse,
    ExtractionTestRequest,
    OverviewResponse,
    RunCreateRequest,
    RunCreateResponse,
    SourceObservationResponse,
)
from aeropex_api.db.models import Agent, AgentRun, ErrorEvent, Source
from aeropex_api.db.session import get_db_session
from aeropex_api.services.configuration import (
    ConfigurationError,
    ConfigurationNotFoundError,
    DuplicateConfigurationError,
    InvalidConfigurationTransition,
    ProductService,
    SourceService,
)
from aeropex_api.services.connectors import ConnectorExecutionService
from aeropex_api.services.extraction import ExtractionService
from aeropex_api.services.run_lifecycle import AgentNotFoundError, AgentRunService, make_id, utc_now

api_router = APIRouter()
SessionDep = Annotated[Session, Depends(get_db_session)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]
AgentIdQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


def _configuration_error_to_http(exc: ConfigurationError) -> HTTPException:
    if isinstance(exc, ConfigurationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration entity not found")
    if isinstance(exc, DuplicateConfigurationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, InvalidConfigurationTransition):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@api_router.get("/health", tags=["system"])
async def versioned_health() -> dict[str, str]:
    return {"status": "healthy", "service": "aeropex-api", "api_version": "v1"}


@api_router.get("/agents", response_model=list[AgentResponse], tags=["agents"])
def list_agents(session: SessionDep) -> list[Agent]:
    return session.query(Agent).order_by(Agent.agent_id).all()


@api_router.get("/products", response_model=list[ProductRead], tags=["products"])
def list_products(
    session: SessionDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    active: bool | None = None,
    category: str | None = None,
) -> list:
    return ProductService(session).list_products(limit=limit, offset=offset, active=active, category=category)


@api_router.get("/products/{product_id}", response_model=ProductRead, tags=["products"])
def get_product(product_id: str, session: SessionDep) -> object:
    product = ProductService(session).get_product(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@api_router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED, tags=["products"])
def create_product(payload: ProductCreate, session: SessionDep) -> object:
    try:
        return ProductService(session).create_product(payload)
    except ConfigurationError as exc:
        session.rollback()
        raise _configuration_error_to_http(exc) from exc


@api_router.patch("/products/{product_id}", response_model=ProductRead, tags=["products"])
def update_product(product_id: str, payload: ProductUpdate, session: SessionDep) -> object:
    try:
        return ProductService(session).update_product(product_id, payload)
    except ConfigurationError as exc:
        session.rollback()
        raise _configuration_error_to_http(exc) from exc


@api_router.get("/sources/eligible", response_model=list[SourceRead], tags=["sources"])
def list_eligible_sources(
    session: SessionDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> list:
    return SourceService(session).list_eligible_sources(limit=limit, offset=offset)


@api_router.get("/sources", response_model=list[SourceRead], tags=["sources"])
def list_sources(
    session: SessionDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    approval_status: SourceApprovalStatus | None = None,
    operational_status: SourceOperationalStatus | None = None,
) -> list:
    return SourceService(session).list_sources(
        limit=limit,
        offset=offset,
        approval_status=approval_status,
        operational_status=operational_status,
    )


@api_router.get("/sources/{source_id}", response_model=SourceRead, tags=["sources"])
def get_source(source_id: str, session: SessionDep) -> object:
    source = SourceService(session).get_source(source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@api_router.post("/connectors/test", response_model=ConnectorResultResponse, tags=["connectors"])
async def test_connector(payload: ConnectorTestRequest, request: Request, session: SessionDep) -> object:
    return await ConnectorExecutionService(session, request.app.state.settings).execute_test(
        source_id=payload.source_id,
        target_url=payload.target_url,
        run_id=payload.run_id,
    )


@api_router.post(
    "/extractions/test",
    response_model=SourceObservationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["extractions"],
)
def test_extraction(payload: ExtractionTestRequest, session: SessionDep) -> object:
    if session.get(Source, payload.source_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    connector_result = ConnectorResult(
        request_id=make_id("REQ"),
        run_id=payload.run_id or make_id("RUN"),
        source_id=payload.source_id,
        target_url=payload.target_url,
        status=ConnectorStatus.SUCCESS,
        http_status_code=200,
        content_type=payload.content_type,
        retrieved_at=utc_now(),
        duration_ms=0,
        attempt_count=1,
        raw_content=payload.raw_content,
    )
    observation = ExtractionService(session).extract_from_connector_result(connector_result)
    if observation is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Extraction was skipped")
    return observation


@api_router.get("/observations", response_model=list[SourceObservationResponse], tags=["observations"])
def list_observations(
    session: SessionDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    source_id: str | None = None,
    run_id: str | None = None,
    product_id: str | None = None,
    extraction_status: ExtractionStatus | None = None,
) -> list:
    return ExtractionService(session).list_observations(
        limit=limit,
        offset=offset,
        source_id=source_id,
        run_id=run_id,
        product_id=product_id,
        extraction_status=extraction_status,
    )


@api_router.get(
    "/observations/{observation_id}",
    response_model=SourceObservationResponse,
    tags=["observations"],
)
def get_observation(observation_id: str, session: SessionDep) -> object:
    observation = ExtractionService(session).get_observation(observation_id)
    if observation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observation not found")
    return observation


@api_router.post("/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED, tags=["sources"])
def create_source(payload: SourceCreate, session: SessionDep) -> object:
    try:
        return SourceService(session).create_source(payload)
    except ConfigurationError as exc:
        session.rollback()
        raise _configuration_error_to_http(exc) from exc


@api_router.patch("/sources/{source_id}", response_model=SourceRead, tags=["sources"])
def update_source(source_id: str, payload: SourceUpdate, session: SessionDep) -> object:
    try:
        return SourceService(session).update_source(source_id, payload)
    except ConfigurationError as exc:
        session.rollback()
        raise _configuration_error_to_http(exc) from exc


@api_router.post("/sources/{source_id}/approve", response_model=SourceRead, tags=["sources"])
def approve_source(source_id: str, session: SessionDep) -> object:
    try:
        return SourceService(session).approve_source(source_id)
    except ConfigurationError as exc:
        session.rollback()
        raise _configuration_error_to_http(exc) from exc


@api_router.post("/sources/{source_id}/reject", response_model=SourceRead, tags=["sources"])
def reject_source(source_id: str, session: SessionDep) -> object:
    try:
        return SourceService(session).reject_source(source_id)
    except ConfigurationError as exc:
        session.rollback()
        raise _configuration_error_to_http(exc) from exc


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
