"""Connector-specific exceptions."""

from __future__ import annotations


class ConnectorError(ValueError):
    """Base class for connector failures."""


class UnsupportedConnectorError(ConnectorError):
    """Raised when a source access method has no connector implementation."""


class ConnectorGovernanceError(ConnectorError):
    """Raised when source governance rejects connector execution."""


class ConnectorDomainMismatchError(ConnectorGovernanceError):
    """Raised when the requested URL is outside the source's governed domain."""


class ConnectorUnsafeTargetError(ConnectorGovernanceError):
    """Raised when the target URL is malformed or points to an unsafe destination."""


class ConnectorResponseTooLargeError(ConnectorError):
    """Raised when an HTTP response exceeds the configured body limit."""
