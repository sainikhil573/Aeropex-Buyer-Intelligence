"""Connector factory for source access methods."""

from __future__ import annotations

from aeropex_contracts.enums import SourceAccessMethod

from aeropex_api.connectors.base import Connector
from aeropex_api.connectors.exceptions import UnsupportedConnectorError
from aeropex_api.connectors.http import HttpConnector
from aeropex_api.core.config import Settings


class ConnectorFactory:
    """Resolve connector implementations without leaking access details to callers."""

    def __init__(self, settings: Settings, *, http_connector: Connector | None = None) -> None:
        self.settings = settings
        self._http_connector = http_connector

    def create(self, access_method: SourceAccessMethod) -> Connector:
        if access_method == SourceAccessMethod.HTTP:
            return self._http_connector or HttpConnector(self.settings)
        raise UnsupportedConnectorError(f"Unsupported connector access method: {access_method.value}")
