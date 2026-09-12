"""API schemas for operational endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from aeropex_contracts.enums import AgentStatus, AuthorityLevel, RunStatus, TriggerType
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


class ReadinessCheck(BaseModel):
    status: str
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    service: str
    checks: dict[str, ReadinessCheck | dict[str, Any]]
