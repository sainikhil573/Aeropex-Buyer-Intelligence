"""Extractor interface definitions."""

from __future__ import annotations

from typing import Protocol

from aeropex_contracts.models import ExtractionRequest, ExtractionResult


class Extractor(Protocol):
    """Typed extractor boundary: interpret source content, do not persist it."""

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        """Extract a bounded candidate observation from source content."""
