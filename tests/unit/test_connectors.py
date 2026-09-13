from __future__ import annotations

import asyncio
from datetime import UTC

import httpx
import pytest
from aeropex_api.connectors.exceptions import UnsupportedConnectorError
from aeropex_api.connectors.factory import ConnectorFactory
from aeropex_api.connectors.http import HttpConnector
from aeropex_api.core.config import Settings
from aeropex_api.db.base import Base, import_models
from aeropex_api.db.models import Buyer, BuyerRequirement, ErrorEvent, Source
from aeropex_api.db.session import get_db_session
from aeropex_api.main import create_app
from aeropex_api.services.configuration import SourceService
from aeropex_api.services.connectors import ConnectorExecutionService
from aeropex_api.services.run_lifecycle import utc_now
from aeropex_contracts.enums import (
    ConnectorStatus,
    SourceAccessMethod,
    SourceApprovalStatus,
    SourceOperationalStatus,
)
from aeropex_contracts.models import ConnectorRequest, SourceCreate
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
        yield db_session


def make_source(
    session: Session,
    source_id: str = "SRC-HTTP",
    *,
    access_method: SourceAccessMethod = SourceAccessMethod.HTTP,
    approval_status: SourceApprovalStatus = SourceApprovalStatus.APPROVED,
    operational_status: SourceOperationalStatus = SourceOperationalStatus.ACTIVE,
    domain: str = "example.com",
) -> Source:
    source = SourceService(session).create_source(
        SourceCreate(
            source_id=source_id,
            name=source_id,
            domain=domain,
            source_type="directory",
            access_method=access_method,
            operational_status=operational_status,
        )
    )
    source.approval_status = approval_status
    source.operational_status = operational_status
    session.commit()
    session.refresh(source)
    return source


def request(url: str = "https://example.com/resource") -> ConnectorRequest:
    return ConnectorRequest(
        request_id="REQ-1",
        run_id="RUN-1",
        source_id="SRC-HTTP",
        target_url=url,
        method="GET",
        requested_at=utc_now(),
    )


def connector_with_transport(
    handler: httpx.MockTransport | httpx.AsyncBaseTransport,
    *,
    settings: Settings | None = None,
) -> HttpConnector:
    def client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=handler,
            timeout=httpx.Timeout((settings or Settings()).connector_http_timeout_seconds),
            follow_redirects=True,
        )

    return HttpConnector(settings or Settings(), client_factory=client_factory)


def run(coro):
    return asyncio.run(coro)


def test_connector_factory_resolves_http() -> None:
    connector = ConnectorFactory(Settings()).create(SourceAccessMethod.HTTP)

    assert isinstance(connector, HttpConnector)


def test_connector_factory_rejects_unsupported_methods() -> None:
    factory = ConnectorFactory(Settings())

    with pytest.raises(UnsupportedConnectorError):
        factory.create(SourceAccessMethod.API)


def test_candidate_rejected_and_disabled_sources_cannot_execute(session: Session) -> None:
    service = ConnectorExecutionService(session, Settings())
    cases = [
        ("SRC-CANDIDATE", SourceApprovalStatus.CANDIDATE, SourceOperationalStatus.ACTIVE),
        ("SRC-REJECTED", SourceApprovalStatus.REJECTED, SourceOperationalStatus.ACTIVE),
        ("SRC-DISABLED", SourceApprovalStatus.APPROVED, SourceOperationalStatus.DISABLED),
    ]
    for source_id, approval, operational in cases:
        make_source(
            session,
            source_id,
            approval_status=approval,
            operational_status=operational,
        )

        result = run(service.execute_test(source_id=source_id, target_url="https://example.com/data"))

        assert result.status == ConnectorStatus.BLOCKED
        assert result.raw_content is None


def test_approved_active_source_can_execute(session: Session) -> None:
    make_source(session)
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text="ok"))
    settings = Settings()
    factory = ConnectorFactory(settings, http_connector=connector_with_transport(transport, settings=settings))

    result = run(
        ConnectorExecutionService(session, settings, factory=factory).execute_test(
            source_id="SRC-HTTP",
            target_url="https://example.com/data",
            request_id="REQ-KEEP",
            run_id="RUN-KEEP",
        )
    )

    assert result.status == ConnectorStatus.SUCCESS
    assert result.raw_content == "ok"
    assert result.request_id == "REQ-KEEP"
    assert result.run_id == "RUN-KEEP"
    assert result.source_id == "SRC-HTTP"


@pytest.mark.parametrize(
    "url,error_type",
    [
        ("https://not-example.com/data", "connector_domain_mismatch"),
        ("not-a-url", "connector_blocked"),
        ("file://example.com/data", "connector_blocked"),
        ("ftp://example.com/data", "connector_blocked"),
        ("http://localhost/data", "connector_blocked"),
        ("http://127.0.0.1/data", "connector_blocked"),
        ("http://10.0.0.4/data", "connector_blocked"),
        ("http://192.168.1.2/data", "connector_blocked"),
        ("http://169.254.169.254/latest/meta-data", "connector_blocked"),
    ],
)
def test_target_url_governance_rejects_unsafe_targets(
    session: Session,
    url: str,
    error_type: str,
) -> None:
    make_source(session, domain="example.com")

    result = run(
        ConnectorExecutionService(session, Settings()).execute_test(
            source_id="SRC-HTTP",
            target_url=url,
        )
    )

    assert result.status == ConnectorStatus.BLOCKED
    assert result.error_type == error_type


def test_unsupported_source_access_method_returns_unsupported(session: Session) -> None:
    make_source(session, access_method=SourceAccessMethod.MANUAL, domain="example.com")

    result = run(
        ConnectorExecutionService(session, Settings()).execute_test(
            source_id="SRC-HTTP",
            target_url="https://example.com/data",
        )
    )

    assert result.status == ConnectorStatus.UNSUPPORTED
    assert result.error_type == "connector_unsupported"


def test_successful_200_response_captures_content_type_status_raw_and_duration() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, text="hello", headers={"content-type": "text/plain"})
    )

    result = run(connector_with_transport(transport).execute(request()))

    assert result.status == ConnectorStatus.SUCCESS
    assert result.http_status_code == 200
    assert result.content_type == "text/plain"
    assert result.raw_content == "hello"
    assert result.duration_ms >= 0
    assert result.attempt_count == 1
    assert result.retrieved_at.tzinfo == UTC


def test_oversized_response_fails_safely() -> None:
    settings = Settings(connector_http_max_response_bytes=2)
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b"large"))

    result = run(connector_with_transport(transport, settings=settings).execute(request()))

    assert result.status == ConnectorStatus.FAILED
    assert result.error_type == "connector_response_too_large"
    assert result.raw_content is None
    assert result.content_truncated is False


def test_timeout_behavior() -> None:
    class TimeoutTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timeout", request=request)

    settings = Settings(connector_http_max_attempts=2)

    result = run(connector_with_transport(TimeoutTransport(), settings=settings).execute(request()))

    assert result.status == ConnectorStatus.TIMEOUT
    assert result.error_type == "connector_timeout"
    assert result.attempt_count == 2


def test_connection_error_behavior() -> None:
    class ConnectionErrorTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connect failed", request=request)

    settings = Settings(connector_http_max_attempts=2)

    result = run(connector_with_transport(ConnectionErrorTransport(), settings=settings).execute(request()))

    assert result.status == ConnectorStatus.FAILED
    assert result.error_type == "connector_connection_error"
    assert result.attempt_count == 2


@pytest.mark.parametrize(
    ("status_code", "expected_status", "expected_attempts", "expected_error"),
    [
        (404, ConnectorStatus.FAILED, 1, "connector_http_error"),
        (403, ConnectorStatus.BLOCKED, 1, "connector_blocked"),
        (429, ConnectorStatus.FAILED, 3, "connector_rate_limited"),
        (500, ConnectorStatus.FAILED, 3, "connector_http_error"),
        (502, ConnectorStatus.FAILED, 3, "connector_http_error"),
        (503, ConnectorStatus.FAILED, 3, "connector_http_error"),
    ],
)
def test_http_status_retry_policy(
    status_code: int,
    expected_status: ConnectorStatus,
    expected_attempts: int,
    expected_error: str,
) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code)

    result = run(connector_with_transport(httpx.MockTransport(handler)).execute(request()))

    assert result.status == expected_status
    assert result.attempt_count == expected_attempts
    assert calls == expected_attempts
    assert result.error_type == expected_error


def test_successful_retry_after_temporary_failure() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, text="recovered")

    result = run(connector_with_transport(httpx.MockTransport(handler)).execute(request()))

    assert result.status == ConnectorStatus.SUCCESS
    assert result.raw_content == "recovered"
    assert result.attempt_count == 2


def test_error_event_created_on_final_failure(session: Session) -> None:
    make_source(session)

    result = run(
        ConnectorExecutionService(session, Settings()).execute_test(
            source_id="SRC-HTTP",
            target_url="https://wrong.example.net/data",
        )
    )

    assert result.error_type == "connector_domain_mismatch"
    event = session.query(ErrorEvent).one()
    assert event.error_type == "connector_domain_mismatch"
    assert "response" not in event.message.lower()


def test_no_buyer_entities_are_created(session: Session) -> None:
    make_source(session)
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text="buyer-looking text"))
    settings = Settings()
    factory = ConnectorFactory(settings, http_connector=connector_with_transport(transport, settings=settings))

    run(
        ConnectorExecutionService(session, settings, factory=factory).execute_test(
            source_id="SRC-HTTP",
            target_url="https://example.com/data",
        )
    )

    assert session.query(Buyer).count() == 0
    assert session.query(BuyerRequirement).count() == 0


def test_connector_test_api_enforces_governance(session: Session) -> None:
    make_source(session)
    app = create_app(Settings())

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    response = client.post(
        "/api/v1/connectors/test",
        json={"source_id": "SRC-HTTP", "target_url": "https://not-example.com/data"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["error_type"] == "connector_domain_mismatch"
