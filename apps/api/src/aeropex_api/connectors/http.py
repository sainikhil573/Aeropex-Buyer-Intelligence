"""Controlled HTTP connector implementation."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

import httpx
from aeropex_contracts.enums import ConnectorStatus
from aeropex_contracts.models import ConnectorRequest, ConnectorResult

from aeropex_api.connectors.exceptions import ConnectorResponseTooLargeError
from aeropex_api.core.config import Settings
from aeropex_api.services.run_lifecycle import utc_now

logger = logging.getLogger(__name__)

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
BLOCKED_STATUSES = {401, 403}


class HttpConnector:
    """HTTP GET connector with bounded timeout, retry, redirect, and body controls."""

    def __init__(
        self,
        settings: Settings,
        *,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self.settings = settings
        self._client_factory = client_factory

    async def execute(self, request: ConnectorRequest) -> ConnectorResult:
        started = time.perf_counter()
        max_attempts = max(1, self.settings.connector_http_max_attempts)
        last_http_status: int | None = None
        last_content_type: str | None = None
        last_error_type = "connector_http_error"
        last_error_message = "HTTP connector execution failed"

        for attempt in range(1, max_attempts + 1):
            try:
                result = await self._attempt(request, started, attempt)
                if result.status == ConnectorStatus.SUCCESS:
                    self._log_result(request, attempt, result)
                    return result
                last_http_status = result.http_status_code
                last_content_type = result.content_type
                last_error_type = result.error_type or last_error_type
                last_error_message = result.error_message or last_error_message
                if not self._should_retry_status(result.http_status_code, attempt, max_attempts):
                    self._log_result(request, attempt, result)
                    return result
            except httpx.TimeoutException:
                last_error_type = "connector_timeout"
                last_error_message = "HTTP connector timed out"
                if attempt == max_attempts:
                    return self._failure_result(
                        request,
                        started,
                        attempt,
                        ConnectorStatus.TIMEOUT,
                        last_error_type,
                        last_error_message,
                    )
            except httpx.TransportError:
                last_error_type = "connector_connection_error"
                last_error_message = "HTTP connector connection error"
                if attempt == max_attempts:
                    return self._failure_result(
                        request,
                        started,
                        attempt,
                        ConnectorStatus.FAILED,
                        last_error_type,
                        last_error_message,
                    )
            except ConnectorResponseTooLargeError as exc:
                return self._failure_result(
                    request,
                    started,
                    attempt,
                    ConnectorStatus.FAILED,
                    "connector_response_too_large",
                    str(exc),
                )

            await asyncio.sleep(min(0.2 * attempt, 1.0))

        return self._failure_result(
            request,
            started,
            max_attempts,
            ConnectorStatus.FAILED,
            last_error_type,
            last_error_message,
            http_status_code=last_http_status,
            content_type=last_content_type,
        )

    async def _attempt(
        self,
        request: ConnectorRequest,
        started: float,
        attempt: int,
    ) -> ConnectorResult:
        async with self._client() as client:
            response = await client.get(
                request.target_url,
                headers=self._headers(request),
                params=request.query_params,
            )
            content_type = response.headers.get("content-type")
            raw_bytes = response.content
            if len(raw_bytes) > self.settings.connector_http_max_response_bytes:
                raise ConnectorResponseTooLargeError(
                    "HTTP response exceeded configured maximum body size"
                )

            if 200 <= response.status_code <= 299:
                return ConnectorResult(
                    request_id=request.request_id,
                    run_id=request.run_id,
                    source_id=request.source_id,
                    target_url=request.target_url,
                    status=ConnectorStatus.SUCCESS,
                    http_status_code=response.status_code,
                    content_type=content_type,
                    retrieved_at=utc_now(),
                    duration_ms=self._duration_ms(started),
                    attempt_count=attempt,
                    raw_content=response.text,
                )

            status = ConnectorStatus.BLOCKED if response.status_code in BLOCKED_STATUSES else ConnectorStatus.FAILED
            error_type = "connector_blocked" if status == ConnectorStatus.BLOCKED else "connector_http_error"
            if response.status_code == 429:
                error_type = "connector_rate_limited"
            return self._failure_result(
                request,
                started,
                attempt,
                status,
                error_type,
                f"HTTP connector received status {response.status_code}",
                http_status_code=response.status_code,
                content_type=content_type,
            )

    def _client(self) -> httpx.AsyncClient:
        if self._client_factory is not None:
            return self._client_factory()
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.connector_http_timeout_seconds),
            follow_redirects=True,
            max_redirects=self.settings.connector_http_max_redirects,
        )

    def _headers(self, request: ConnectorRequest) -> dict[str, str]:
        headers = {key: value for key, value in request.headers.items() if key.lower() != "host"}
        headers.setdefault("User-Agent", self.settings.connector_user_agent)
        return headers

    @staticmethod
    def _should_retry_status(status_code: int | None, attempt: int, max_attempts: int) -> bool:
        return status_code in RETRYABLE_STATUSES and attempt < max_attempts

    @staticmethod
    def _duration_ms(started: float) -> int:
        return max(0, round((time.perf_counter() - started) * 1000))

    def _failure_result(
        self,
        request: ConnectorRequest,
        started: float,
        attempt: int,
        status: ConnectorStatus,
        error_type: str,
        error_message: str,
        *,
        http_status_code: int | None = None,
        content_type: str | None = None,
    ) -> ConnectorResult:
        result = ConnectorResult(
            request_id=request.request_id,
            run_id=request.run_id,
            source_id=request.source_id,
            target_url=request.target_url,
            status=status,
            http_status_code=http_status_code,
            content_type=content_type,
            retrieved_at=utc_now(),
            duration_ms=self._duration_ms(started),
            attempt_count=attempt,
            raw_content=None,
            error_type=error_type,
            error_message=error_message,
        )
        self._log_result(request, attempt, result)
        return result

    def _log_result(self, request: ConnectorRequest, attempt: int, result: ConnectorResult) -> None:
        logger.info(
            "connector_http_result",
            extra={
                "request_id": request.request_id,
                "run_id": request.run_id,
                "source_id": request.source_id,
                "connector_type": "http",
                "target_hostname": httpx.URL(request.target_url).host,
                "attempt": attempt,
                "duration_ms": result.duration_ms,
                "result_status": result.status.value,
                "http_status_code": result.http_status_code,
                "error_type": result.error_type,
            },
        )
