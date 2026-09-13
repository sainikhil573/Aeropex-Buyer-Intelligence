"""Deterministic extractor for controlled JSON source fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from aeropex_contracts.enums import EvidenceType, ExtractionStatus
from aeropex_contracts.models import ExtractionRequest, ExtractionResult, ProductContext


class StructuredJsonExtractor:
    extractor_type = "structured_json"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        raw_text = request.raw_content
        if not raw_text or not raw_text.strip():
            return self._failed(request, "extractor_invalid_payload", "raw_content is required")
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return self._failed(request, "extractor_invalid_payload", f"Invalid JSON payload: {exc.msg}")
        if not isinstance(payload, dict):
            return self._failed(request, "extractor_invalid_payload", "JSON payload must be an object")

        contact = payload.get("contact")
        contact_payload = contact if isinstance(contact, dict) else {}
        product_name = self._clean(payload.get("product") or payload.get("product_name"))
        quantity, quantity_error = self._parse_quantity(payload.get("quantity"))
        posted_at, posted_error = self._parse_posted_at(payload.get("posted_at"))
        product_id = self._match_product(product_name, request.product_context)
        fields = {
            "company_name": self._clean(payload.get("company_name")),
            "country": self._clean(payload.get("country")),
            "product_name": product_name,
            "product_id": product_id,
            "requirement_text": self._clean(payload.get("requirement") or payload.get("requirement_text")),
            "quantity": quantity,
            "unit": self._clean(payload.get("unit")),
            "specifications": payload.get("specifications") if isinstance(payload.get("specifications"), dict) else {},
            "contact_name": self._clean(contact_payload.get("name") or payload.get("contact_name")),
            "contact_email": self._clean_email(contact_payload.get("email") or payload.get("contact_email")),
            "contact_phone": self._clean(contact_payload.get("phone") or payload.get("contact_phone")),
            "posted_at": posted_at,
        }
        useful_count = sum(
            value not in (None, "", {}) for key, value in fields.items() if key not in {"product_name"}
        )
        status = ExtractionStatus.UNSTRUCTURED
        if useful_count >= 3:
            status = ExtractionStatus.SUCCESS
        elif useful_count > 0:
            status = ExtractionStatus.PARTIAL

        error_type = quantity_error or posted_error
        return ExtractionResult(
            request_id=request.request_id,
            run_id=request.run_id,
            source_id=request.source_id,
            source_url=request.source_url,
            status=status,
            confidence_score=Decimal("1.0") if status == ExtractionStatus.SUCCESS else None,
            evidence_type=EvidenceType.API_RECORD,
            raw_text=raw_text,
            extractor_type=self.extractor_type,
            error_type=error_type,
            error_message="One or more optional fields could not be parsed" if error_type else None,
            **fields,
        )

    def _failed(self, request: ExtractionRequest, error_type: str, message: str) -> ExtractionResult:
        return ExtractionResult(
            request_id=request.request_id,
            run_id=request.run_id,
            source_id=request.source_id,
            source_url=request.source_url,
            status=ExtractionStatus.FAILED,
            evidence_type=EvidenceType.UNKNOWN,
            raw_text=request.raw_content,
            extractor_type=self.extractor_type,
            error_type=error_type,
            error_message=message,
        )

    @staticmethod
    def _clean(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @classmethod
    def _clean_email(cls, value: Any) -> str | None:
        cleaned = cls._clean(value)
        return cleaned.lower() if cleaned else None

    @staticmethod
    def _parse_quantity(value: Any) -> tuple[Decimal | None, str | None]:
        if value is None or value == "":
            return None, None
        try:
            return Decimal(str(value)), None
        except (InvalidOperation, ValueError):
            return None, "extractor_parse_error"

    @staticmethod
    def _parse_posted_at(value: Any) -> tuple[datetime | None, str | None]:
        if value is None or value == "":
            return None, None
        if not isinstance(value, str):
            return None, "extractor_parse_error"
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None, "extractor_parse_error"
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None, "extractor_parse_error"
        return parsed.astimezone(UTC), None

    @classmethod
    def _match_product(cls, product_name: str | None, products: list[ProductContext]) -> str | None:
        normalized_name = cls._normalize_match_text(product_name)
        if normalized_name is None:
            return None
        matches: set[str] = set()
        for product in products:
            candidates = [product.name, *product.aliases, *product.variants]
            if normalized_name in {cls._normalize_match_text(candidate) for candidate in candidates}:
                matches.add(product.product_id)
        if len(matches) == 1:
            return next(iter(matches))
        return None

    @staticmethod
    def _normalize_match_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.casefold().strip().split())
        return cleaned or None
