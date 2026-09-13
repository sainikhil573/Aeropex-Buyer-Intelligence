"""Connector interface definitions."""

from __future__ import annotations

from typing import Protocol

from aeropex_contracts.models import ConnectorRequest, ConnectorResult


class Connector(Protocol):
    """Typed connector boundary: acquire data, do not interpret it."""

    async def execute(self, request: ConnectorRequest) -> ConnectorResult:
        """Execute a governed source retrieval request."""
