"""Pydantic implementations of the approved V0.1 data contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_validator

from aeropex_contracts.enums import (
    AgentStatus,
    ApprovalStatus,
    AuthorityLevel,
    ErrorSeverity,
    RunStatus,
    SourceAccessMethod,
    SourceApprovalStatus,
    SourceOperationalStatus,
    TriggerType,
    VerificationStatus,
)


class ContractModel(BaseModel):
    """Base settings shared by all data contract models."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("*", mode="after")
    @classmethod
    def validate_timezone_aware_datetimes(cls, value: Any) -> Any:
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("datetime values must be timezone-aware")
        return value


Score = Decimal
NonNegativeInt = int


class Agent(ContractModel):
    agent_id: str
    name: str
    type: str
    status: AgentStatus
    version: str
    authority_level: AuthorityLevel
    created_at: datetime
    updated_at: datetime
    capabilities: list[str] = Field(default_factory=list)
    last_heartbeat_at: datetime | None = None


class AgentRun(ContractModel):
    run_id: str
    agent_id: str
    trigger_type: TriggerType
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    records_processed: NonNegativeInt = Field(default=0, ge=0)
    records_created: NonNegativeInt = Field(default=0, ge=0)
    retry_count: NonNegativeInt = Field(default=0, ge=0)
    error_count: NonNegativeInt = Field(default=0, ge=0)
    summary: str | None = None


class Source(ContractModel):
    source_id: str
    name: str
    source_type: str
    access_method: SourceAccessMethod
    approval_status: SourceApprovalStatus
    operational_status: SourceOperationalStatus
    domain: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)
    reliability_score: Score | None = Field(default=None, ge=0, le=1)
    last_checked_at: datetime | None = None
    notes: str | None = None
    product_relevance: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Product(ContractModel):
    product_id: str
    category: str
    name: str
    active: bool
    aliases: list[str] = Field(default_factory=list)
    variants: list[str] = Field(default_factory=list)
    hs_codes: list[str] = Field(default_factory=list)
    priority: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductCreate(ContractModel):
    product_id: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list)
    variants: list[str] = Field(default_factory=list)
    hs_codes: list[str] = Field(default_factory=list)
    priority: int = 100
    active: bool = True


class ProductUpdate(ContractModel):
    category: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    aliases: list[str] | None = None
    variants: list[str] | None = None
    hs_codes: list[str] | None = None
    priority: int | None = None
    active: bool | None = None


class ProductRead(Product):
    created_at: datetime
    updated_at: datetime


class SourceCreate(ContractModel):
    source_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    domain: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    source_type: str = Field(min_length=1, max_length=100)
    access_method: SourceAccessMethod
    operational_status: SourceOperationalStatus = SourceOperationalStatus.ACTIVE
    reliability_score: Score | None = Field(default=None, ge=0, le=1)
    last_checked_at: datetime | None = None
    notes: str | None = None
    product_relevance: list[str] = Field(default_factory=list)


class SourceUpdate(ContractModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    source_type: str | None = Field(default=None, min_length=1, max_length=100)
    access_method: SourceAccessMethod | None = None
    operational_status: SourceOperationalStatus | None = None
    reliability_score: Score | None = Field(default=None, ge=0, le=1)
    last_checked_at: datetime | None = None
    notes: str | None = None
    product_relevance: list[str] | None = None


class SourceRead(Source):
    created_at: datetime
    updated_at: datetime


class Buyer(ContractModel):
    buyer_id: str
    company_name: str
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime
    country: str | None = Field(default=None, min_length=2, max_length=2)
    website: AnyUrl | None = None
    company_type: str | None = None
    confidence_score: Score | None = Field(default=None, ge=0, le=1)


class BuyerRequirement(ContractModel):
    requirement_id: str
    buyer_id: str
    product_id: str
    requirement_text: str
    status: str
    quantity: Decimal | None = None
    unit: str | None = None
    specifications: dict[str, Any] = Field(default_factory=dict)
    destination: str | None = None
    posted_at: datetime | None = None


class SourceObservation(ContractModel):
    observation_id: str
    source_id: str
    run_id: str
    captured_at: datetime
    buyer_id: str | None = None
    requirement_id: str | None = None
    source_url: AnyUrl | None = None
    raw_text: str | None = None
    evidence_type: str | None = None
    confidence_score: Score | None = Field(default=None, ge=0, le=1)


class ErrorEvent(ContractModel):
    error_id: str
    error_type: str
    severity: ErrorSeverity
    message: str
    retryable: bool
    resolved: bool
    created_at: datetime
    run_id: str | None = None
    agent_id: str | None = None


class Approval(ContractModel):
    approval_id: str
    entity_type: str
    entity_id: str
    action_type: str
    requested_by: str
    status: ApprovalStatus
    created_at: datetime
    approved_by: str | None = None
    resolved_at: datetime | None = None


class AuditEvent(ContractModel):
    audit_id: str
    actor_type: str
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
