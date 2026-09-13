"""API schemas for operational endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from aeropex_contracts.enums import (
    AgentStatus,
    AuthorityLevel,
    BuyerRequirementStatus,
    ConnectorStatus,
    EntityResolutionStatus,
    ErrorSeverity,
    EvidenceType,
    ExtractionStatus,
    ObservationReviewStatus,
    RunStatus,
    TriggerType,
    VerificationStatus,
)
from pydantic import BaseModel, ConfigDict, Field


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    name: str
    type: str
    status: AgentStatus
    version: str
    capabilities: list[str]
    authority_level: AuthorityLevel
    last_heartbeat_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    agent_id: str
    trigger_type: TriggerType
    status: RunStatus
    started_at: datetime | None
    finished_at: datetime | None
    records_processed: int
    records_created: int
    retry_count: int
    error_count: int
    summary: str | None


class RunCreateRequest(BaseModel):
    agent_id: str = "AGT-BUYER-DISCOVERY-001"
    trigger_type: TriggerType = TriggerType.MANUAL
    run_id: str | None = Field(default=None, min_length=1, max_length=64)
    simulate_failure: bool = False


class RunCreateResponse(AgentRunResponse):
    task_id: str | None = None


class ConnectorTestRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=64)
    target_url: str = Field(min_length=1, max_length=2048)
    run_id: str | None = Field(default=None, min_length=1, max_length=64)


class ConnectorResultResponse(BaseModel):
    request_id: str
    run_id: str
    source_id: str
    target_url: str
    status: ConnectorStatus
    http_status_code: int | None
    content_type: str | None
    retrieved_at: datetime
    duration_ms: int
    attempt_count: int
    raw_content: str | None
    error_type: str | None
    error_message: str | None
    content_truncated: bool


class ExtractionTestRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=64)
    run_id: str | None = Field(default=None, min_length=1, max_length=64)
    target_url: str = Field(default="https://controlled-fixture.local/record", min_length=1, max_length=2048)
    content_type: str = "application/json"
    raw_content: str = Field(min_length=1, max_length=200_000)


class SourceObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    observation_id: str
    source_id: str
    run_id: str
    source_url: str | None
    captured_at: datetime
    raw_text: str | None
    evidence_type: EvidenceType
    confidence_score: float | None
    buyer_id: str | None
    requirement_id: str | None
    product_id: str | None
    company_name: str | None
    country: str | None
    requirement_text: str | None
    quantity: float | None
    unit: str | None
    specifications: dict[str, Any]
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    posted_at: datetime | None
    extraction_status: ExtractionStatus
    extractor_type: str
    metadata: dict[str, Any] = Field(validation_alias="observation_metadata")
    review_status: ObservationReviewStatus = ObservationReviewStatus.UNREVIEWED
    review_notes: str | None = None
    review_id: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_created_at: datetime | None = None
    review_updated_at: datetime | None = None


class BuyerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    buyer_id: str
    company_name: str
    normalized_company_name: str
    country: str | None
    website: str | None
    primary_domain: str | None
    company_type: str | None
    verification_status: VerificationStatus
    confidence_score: float | None
    created_at: datetime
    updated_at: datetime
    requirements_count: int | None = None


class BuyerRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requirement_id: str
    buyer_id: str
    product_id: str | None
    requirement_text: str | None
    quantity: float | None
    unit: str | None
    specifications: dict[str, Any]
    destination: str | None
    posted_at: datetime | None
    status: BuyerRequirementStatus
    created_at: datetime
    updated_at: datetime


class CanonicalizationResultResponse(BaseModel):
    status: EntityResolutionStatus
    observation_id: str
    buyer_id: str | None
    requirement_id: str | None
    matched_existing_buyer: bool
    candidate_buyer_ids: list[str]
    reason: str | None


class ObservationReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: str | None
    observation_id: str
    status: ObservationReviewStatus
    review_notes: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None


class UpdateObservationReviewRequest(BaseModel):
    status: ObservationReviewStatus
    review_notes: str | None = Field(default=None, max_length=10_000)


class ErrorEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    error_id: str
    run_id: str | None
    agent_id: str | None
    error_type: str
    severity: ErrorSeverity
    message: str
    retryable: bool
    resolved: bool
    created_at: datetime


class OverviewResponse(BaseModel):
    platform_status: str
    total_agents: int
    running_agents: int
    recent_runs: int
    failed_runs: int
    unreviewed_observations: int = 0
    needs_review_observations: int = 0
    accepted_observations: int = 0
    rejected_observations: int = 0


class ReadinessCheck(BaseModel):
    status: str
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    service: str
    checks: dict[str, ReadinessCheck | dict[str, Any]]
