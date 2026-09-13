from datetime import UTC, datetime

import pytest
from aeropex_contracts import (
    Agent,
    AgentRun,
    AgentStatus,
    AuthorityLevel,
    Buyer,
    BuyerRequirement,
    ConnectorRequest,
    ConnectorResult,
    ConnectorStatus,
    RunStatus,
    Source,
    SourceApprovalStatus,
    SourceObservation,
    SourceOperationalStatus,
    TriggerType,
    VerificationStatus,
)
from pydantic import ValidationError

NOW = datetime(2026, 9, 12, 1, 30, tzinfo=UTC)


def test_valid_contract_creation() -> None:
    agent = Agent(
        agent_id="AGT-BUYER-DISCOVERY-001",
        name="Buyer Discovery",
        type="buyer_discovery",
        status=AgentStatus.ACTIVE,
        version="0.1.0",
        authority_level=AuthorityLevel.GREEN,
        created_at=NOW,
        updated_at=NOW,
    )

    assert agent.agent_id == "AGT-BUYER-DISCOVERY-001"
    assert agent.capabilities == []


def test_required_field_validation() -> None:
    with pytest.raises(ValidationError):
        Agent(
            name="Buyer Discovery",
            type="buyer_discovery",
            status=AgentStatus.ACTIVE,
            version="0.1.0",
            authority_level=AuthorityLevel.GREEN,
            created_at=NOW,
            updated_at=NOW,
        )


def test_invalid_enum_rejection() -> None:
    with pytest.raises(ValidationError):
        Agent(
            agent_id="AGT-001",
            name="Buyer Discovery",
            type="buyer_discovery",
            status="paused",
            version="0.1.0",
            authority_level=AuthorityLevel.GREEN,
            created_at=NOW,
            updated_at=NOW,
        )


@pytest.mark.parametrize("score", ["0.0", "1.0"])
def test_confidence_score_boundaries(score: str) -> None:
    buyer = Buyer(
        buyer_id="BUY-000001",
        company_name="ABC Foods LLC",
        verification_status=VerificationStatus.UNVERIFIED,
        created_at=NOW,
        updated_at=NOW,
        confidence_score=score,
    )

    assert buyer.confidence_score is not None


def test_confidence_score_rejects_out_of_range_values() -> None:
    with pytest.raises(ValidationError):
        SourceObservation(
            observation_id="OBS-000001",
            source_id="SRC-0001",
            run_id="RUN-000001",
            captured_at=NOW,
            confidence_score="1.01",
        )


@pytest.mark.parametrize("score", ["0.0", "1.0"])
def test_reliability_score_boundaries(score: str) -> None:
    source = Source(
        source_id="SRC-0001",
        name="Example Trade Portal",
        source_type="trade_portal",
        access_method="http",
        approval_status=SourceApprovalStatus.APPROVED,
        operational_status=SourceOperationalStatus.ACTIVE,
        reliability_score=score,
    )

    assert source.reliability_score is not None


def test_reliability_score_rejects_out_of_range_values() -> None:
    with pytest.raises(ValidationError):
        Source(
            source_id="SRC-0001",
            name="Example Trade Portal",
            source_type="trade_portal",
            access_method="http",
            approval_status=SourceApprovalStatus.APPROVED,
            operational_status=SourceOperationalStatus.ACTIVE,
            reliability_score="-0.01",
        )


def test_non_negative_counters() -> None:
    with pytest.raises(ValidationError):
        AgentRun(
            run_id="RUN-000001",
            agent_id="AGT-001",
            trigger_type=TriggerType.MANUAL,
            status=RunStatus.RUNNING,
            started_at=NOW,
            records_processed=-1,
        )


def test_nullable_optional_fields() -> None:
    requirement = BuyerRequirement(
        requirement_id="REQ-000001",
        buyer_id="BUY-000001",
        product_id="PRD-RED-CHILLI",
        requirement_text="Seeking dried red chilli.",
        status="open",
        quantity=None,
        destination=None,
        posted_at=None,
    )

    assert requirement.quantity is None
    assert requirement.destination is None
    assert requirement.specifications == {}


def test_serialization_deserialization() -> None:
    buyer = Buyer(
        buyer_id="BUY-000001",
        company_name="ABC Foods LLC",
        country="AE",
        website="https://example.com",
        company_type="importer_distributor",
        verification_status=VerificationStatus.UNVERIFIED,
        confidence_score="0.71",
        created_at=NOW,
        updated_at=NOW,
    )

    payload = buyer.model_dump_json()
    restored = Buyer.model_validate_json(payload)

    assert restored == buyer


def test_timezone_aware_datetime_required() -> None:
    with pytest.raises(ValidationError):
        Buyer(
            buyer_id="BUY-000001",
            company_name="ABC Foods LLC",
            verification_status=VerificationStatus.UNVERIFIED,
            created_at=datetime(2026, 9, 12, 1, 30),  # noqa: DTZ001
            updated_at=NOW,
        )


def test_connector_request_contract_defaults_and_utc_validation() -> None:
    request = ConnectorRequest(
        request_id="REQ-000001",
        run_id="RUN-000001",
        source_id="SRC-000001",
        target_url="https://example.com/data",
        requested_at=NOW,
    )

    assert request.method == "GET"
    assert request.headers == {}
    assert request.query_params == {}

    with pytest.raises(ValidationError):
        ConnectorRequest(
            request_id="REQ-000001",
            run_id="RUN-000001",
            source_id="SRC-000001",
            target_url="https://example.com/data",
            method="POST",
            requested_at=NOW,
        )
    with pytest.raises(ValidationError):
        ConnectorRequest(
            request_id="REQ-000001",
            run_id="RUN-000001",
            source_id="SRC-000001",
            target_url="https://example.com/data",
            requested_at=datetime(2026, 9, 12, 1, 30),  # noqa: DTZ001
        )


def test_connector_result_contract_success_and_failure_rules() -> None:
    success = ConnectorResult(
        request_id="REQ-000001",
        run_id="RUN-000001",
        source_id="SRC-000001",
        target_url="https://example.com/data",
        status=ConnectorStatus.SUCCESS,
        http_status_code=200,
        content_type="text/plain",
        retrieved_at=NOW,
        duration_ms=12,
        attempt_count=1,
        raw_content="ok",
    )

    assert success.status == ConnectorStatus.SUCCESS
    assert success.error_type is None

    failed = ConnectorResult(
        request_id="REQ-000001",
        run_id="RUN-000001",
        source_id="SRC-000001",
        target_url="https://example.com/data",
        status=ConnectorStatus.FAILED,
        retrieved_at=NOW,
        duration_ms=0,
        attempt_count=1,
        error_type="connector_http_error",
        error_message="HTTP connector received status 404",
    )

    assert failed.http_status_code is None
    assert failed.raw_content is None


@pytest.mark.parametrize(
    "payload",
    [
        {"duration_ms": -1, "attempt_count": 1},
        {"duration_ms": 0, "attempt_count": 0},
    ],
)
def test_connector_result_rejects_invalid_duration_and_attempts(payload: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        ConnectorResult(
            request_id="REQ-000001",
            run_id="RUN-000001",
            source_id="SRC-000001",
            target_url="https://example.com/data",
            status=ConnectorStatus.FAILED,
            retrieved_at=NOW,
            error_type="connector_http_error",
            error_message="failed",
            **payload,
        )


def test_connector_status_enum_values() -> None:
    assert {status.value for status in ConnectorStatus} == {
        "success",
        "failed",
        "timeout",
        "blocked",
        "unsupported",
    }
