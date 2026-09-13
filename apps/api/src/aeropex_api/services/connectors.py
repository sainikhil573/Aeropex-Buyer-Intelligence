"""Governance-aware connector execution service."""

from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlsplit

from aeropex_contracts.enums import (
    ConnectorStatus,
    ErrorSeverity,
    SourceApprovalStatus,
    SourceOperationalStatus,
)
from aeropex_contracts.models import ConnectorRequest, ConnectorResult
from sqlalchemy.orm import Session

from aeropex_api.connectors.exceptions import (
    ConnectorDomainMismatchError,
    ConnectorGovernanceError,
    ConnectorUnsafeTargetError,
    UnsupportedConnectorError,
)
from aeropex_api.connectors.factory import ConnectorFactory
from aeropex_api.core.config import Settings
from aeropex_api.db.models import AgentRun
from aeropex_api.repositories.configuration import SourceRepository
from aeropex_api.services.run_lifecycle import AgentRunService, make_id, utc_now

logger = logging.getLogger(__name__)

UNSAFE_HOSTNAMES = {"localhost"}


class ConnectorExecutionService:
    """Execute source connectors only after Source Registry governance passes."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        factory: ConnectorFactory | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.sources = SourceRepository(session)
        self.factory = factory or ConnectorFactory(settings)
        self.run_service = AgentRunService(session)

    async def execute_test(
        self,
        *,
        source_id: str,
        target_url: str,
        run_id: str | None = None,
        request_id: str | None = None,
    ) -> ConnectorResult:
        request_id = request_id or make_id("REQ")
        run_id = run_id or make_id("RUN")
        source = self.sources.get(source_id)
        if source is None:
            return self._governance_failure(
                request_id,
                run_id,
                source_id,
                target_url,
                ConnectorStatus.FAILED,
                "connector_source_not_found",
                "Source not found",
            )

        try:
            self._validate_source_eligible(source)
            self._validate_target_url(target_url, source.domain)
            connector = self.factory.create(source.access_method)
        except UnsupportedConnectorError as exc:
            return self._governance_failure(
                request_id,
                run_id,
                source_id,
                target_url,
                ConnectorStatus.UNSUPPORTED,
                "connector_unsupported",
                str(exc),
            )
        except ConnectorDomainMismatchError as exc:
            return self._governance_failure(
                request_id,
                run_id,
                source_id,
                target_url,
                ConnectorStatus.BLOCKED,
                "connector_domain_mismatch",
                str(exc),
            )
        except ConnectorGovernanceError as exc:
            return self._governance_failure(
                request_id,
                run_id,
                source_id,
                target_url,
                ConnectorStatus.BLOCKED,
                "connector_blocked",
                str(exc),
            )

        request = ConnectorRequest(
            request_id=request_id,
            run_id=run_id,
            source_id=source_id,
            target_url=target_url,
            method="GET",
            requested_at=utc_now(),
        )
        result = await connector.execute(request)
        if result.status != ConnectorStatus.SUCCESS:
            self._create_error_event(result)
        return result

    def _validate_source_eligible(self, source: object) -> None:
        if source.approval_status != SourceApprovalStatus.APPROVED:
            raise ConnectorGovernanceError("Source is not approved")
        if source.operational_status != SourceOperationalStatus.ACTIVE:
            raise ConnectorGovernanceError("Source is not active")

    def _validate_target_url(self, target_url: str, source_domain: str | None) -> None:
        parts = urlsplit(target_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ConnectorUnsafeTargetError("Target URL must be an absolute http or https URL")
        hostname = parts.hostname.rstrip(".").lower()
        self._reject_unsafe_hostname(hostname)
        allowed_domain = self._normalize_domain(source_domain)
        if allowed_domain is None:
            raise ConnectorDomainMismatchError("Source does not define a governed domain")
        if hostname != allowed_domain and not hostname.endswith(f".{allowed_domain}"):
            raise ConnectorDomainMismatchError("Target hostname is outside the source governed domain")

    def _reject_unsafe_hostname(self, hostname: str) -> None:
        if self.settings.connector_allow_private_networks:
            return
        if hostname in UNSAFE_HOSTNAMES:
            raise ConnectorUnsafeTargetError("Target hostname is not allowed")
        try:
            ip_address = ipaddress.ip_address(hostname)
        except ValueError:
            return
        if (
            ip_address.is_loopback
            or ip_address.is_private
            or ip_address.is_link_local
            or ip_address.is_multicast
            or ip_address.is_reserved
            or ip_address.is_unspecified
        ):
            raise ConnectorUnsafeTargetError("Target IP address is not allowed")

    @staticmethod
    def _normalize_domain(domain: str | None) -> str | None:
        if not domain:
            return None
        candidate = domain.strip().lower()
        if "://" not in candidate:
            candidate = f"https://{candidate}"
        hostname = urlsplit(candidate).hostname
        return hostname.rstrip(".").lower() if hostname else None

    def _governance_failure(
        self,
        request_id: str,
        run_id: str,
        source_id: str,
        target_url: str,
        status: ConnectorStatus,
        error_type: str,
        error_message: str,
    ) -> ConnectorResult:
        result = ConnectorResult(
            request_id=request_id,
            run_id=run_id,
            source_id=source_id,
            target_url=target_url,
            status=status,
            http_status_code=None,
            content_type=None,
            retrieved_at=utc_now(),
            duration_ms=0,
            attempt_count=1,
            raw_content=None,
            error_type=error_type,
            error_message=error_message,
        )
        self._create_error_event(result)
        logger.warning(
            "connector_governance_failure",
            extra={
                "request_id": request_id,
                "run_id": run_id,
                "source_id": source_id,
                "connector_type": "unknown",
                "target_hostname": urlsplit(target_url).hostname,
                "attempt": 1,
                "duration_ms": 0,
                "result_status": status.value,
                "http_status_code": None,
                "error_type": error_type,
            },
        )
        return result

    def _create_error_event(self, result: ConnectorResult) -> None:
        run = self.session.get(AgentRun, result.run_id)
        self.run_service.create_error_event(
            run_id=result.run_id if run is not None else None,
            agent_id=run.agent_id if run is not None else None,
            error_type=result.error_type or "connector_error",
            severity=ErrorSeverity.ERROR,
            message=result.error_message or "Connector execution failed",
            retryable=result.error_type
            in {"connector_timeout", "connector_connection_error", "connector_rate_limited"},
            resolved=False,
        )
