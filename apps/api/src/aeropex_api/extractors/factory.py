"""Extractor resolution."""

from __future__ import annotations

from aeropex_contracts.enums import EvidenceType, ExtractionStatus
from aeropex_contracts.models import ExtractionRequest, ExtractionResult

from aeropex_api.extractors.base import Extractor
from aeropex_api.extractors.structured_json import StructuredJsonExtractor


class UnsupportedExtractor:
    extractor_type = "unsupported"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        return ExtractionResult(
            request_id=request.request_id,
            run_id=request.run_id,
            source_id=request.source_id,
            source_url=request.source_url,
            status=ExtractionStatus.UNSTRUCTURED,
            evidence_type=EvidenceType.UNKNOWN,
            raw_text=request.raw_content,
            extractor_type=self.extractor_type,
            error_type="extractor_unsupported_content",
            error_message="No deterministic extractor supports this content type",
        )


class ExtractorFactory:
    """Resolve deterministic extractors from governed connector metadata."""

    def __init__(self) -> None:
        self._json_extractor = StructuredJsonExtractor()
        self._unsupported = UnsupportedExtractor()

    def create(self, *, content_type: str | None, source_type: str | None = None) -> Extractor:
        del source_type
        normalized = (content_type or "").split(";")[0].strip().lower()
        if normalized in {"application/json", "text/json"}:
            return self._json_extractor
        return self._unsupported
