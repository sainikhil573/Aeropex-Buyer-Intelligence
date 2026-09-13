"""Services for platform-owned product and source configuration."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from aeropex_contracts.enums import SourceApprovalStatus, SourceOperationalStatus
from aeropex_contracts.models import ProductCreate, ProductUpdate, SourceCreate, SourceUpdate
from sqlalchemy.orm import Session

from aeropex_api.db.models import AuditEvent, Product, Source
from aeropex_api.repositories.configuration import ProductRepository, SourceRepository
from aeropex_api.services.run_lifecycle import make_id, utc_now


class ConfigurationError(ValueError):
    """Base class for configuration service validation failures."""


class DuplicateConfigurationError(ConfigurationError):
    """Raised when a configuration entity already exists."""


class ConfigurationNotFoundError(ConfigurationError):
    """Raised when a configuration entity is missing."""


class InvalidConfigurationTransition(ConfigurationError):
    """Raised when a lifecycle transition is not allowed."""


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ConfigurationError(f"{field_name} is required")
    return cleaned


def _clean_list(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    return [cleaned for value in values if (cleaned := value.strip())]


def _state(entity: Product | Source) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in entity.__table__.columns:
        value = getattr(entity, column.name)
        if hasattr(value, "value"):
            value = value.value
        elif isinstance(value, Decimal):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        data[column.name] = value
    return data


class ProductService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ProductRepository(session)

    def create_product(self, payload: ProductCreate) -> Product:
        if self.repository.get(payload.product_id) is not None:
            raise DuplicateConfigurationError(f"Product already exists: {payload.product_id}")

        now = utc_now()
        name = _required_text(payload.name, "Product name")
        category = _required_text(payload.category, "Product category")
        if payload.active and self.repository.active_name_exists(name=name):
            raise DuplicateConfigurationError(f"Active product name already exists: {name}")

        product = Product(
            product_id=_required_text(payload.product_id, "Product ID"),
            category=category,
            name=name,
            aliases=_clean_list(payload.aliases),
            variants=_clean_list(payload.variants),
            hs_codes=_clean_list(payload.hs_codes),
            priority=payload.priority,
            active=payload.active,
            created_at=now,
            updated_at=now,
        )
        self.repository.add(product)
        self._add_audit("product_created", product, None, _state(product))
        self.session.commit()
        self.session.refresh(product)
        return product

    def update_product(self, product_id: str, payload: ProductUpdate) -> Product:
        product = self.repository.get(product_id)
        if product is None:
            raise ConfigurationNotFoundError(product_id)

        before_state = _state(product)
        updates = payload.model_dump(exclude_unset=True)
        if "name" in updates:
            product.name = _required_text(updates["name"], "Product name")
        if "category" in updates:
            product.category = _required_text(updates["category"], "Product category")
        for field in ("aliases", "variants", "hs_codes"):
            if field in updates:
                setattr(product, field, _clean_list(updates[field]))
        if "priority" in updates:
            if updates["priority"] is None or updates["priority"] < 0:
                raise ConfigurationError("Product priority must be non-negative")
            product.priority = updates["priority"]
        if "active" in updates:
            product.active = updates["active"]
        if product.active and self.repository.active_name_exists(name=product.name, excluding_product_id=product.product_id):
            raise DuplicateConfigurationError(f"Active product name already exists: {product.name}")

        product.updated_at = utc_now()
        action = "product_updated"
        if before_state["active"] is not product.active:
            action = "product_activated" if product.active else "product_deactivated"
        self._add_audit(action, product, before_state, _state(product))
        self.session.commit()
        self.session.refresh(product)
        return product

    def get_product(self, product_id: str) -> Product | None:
        return self.repository.get(product_id)

    def list_products(self, *, limit: int, offset: int, active: bool | None = None, category: str | None = None) -> list[Product]:
        return self.repository.list(limit=min(max(limit, 1), 100), offset=max(offset, 0), active=active, category=category)

    def _add_audit(
        self,
        action: str,
        product: Product,
        before_state: dict[str, Any] | None,
        after_state: dict[str, Any] | None,
    ) -> None:
        self.session.add(
            AuditEvent(
                audit_id=make_id("AUD"),
                actor_type="system",
                actor_id="configuration_service",
                action=action,
                entity_type="product",
                entity_id=product.product_id,
                before_state=before_state,
                after_state=after_state,
                timestamp=utc_now(),
            )
        )


class SourceService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SourceRepository(session)

    def create_source(self, payload: SourceCreate) -> Source:
        if self.repository.get(payload.source_id) is not None:
            raise DuplicateConfigurationError(f"Source already exists: {payload.source_id}")

        now = utc_now()
        source = Source(
            source_id=_required_text(payload.source_id, "Source ID"),
            name=_required_text(payload.name, "Source name"),
            domain=_clean_text(payload.domain),
            country=payload.country.strip().upper() if payload.country else None,
            source_type=_required_text(payload.source_type, "Source type"),
            access_method=payload.access_method,
            approval_status=SourceApprovalStatus.CANDIDATE,
            operational_status=payload.operational_status,
            reliability_score=payload.reliability_score,
            last_checked_at=payload.last_checked_at,
            notes=_clean_text(payload.notes),
            product_relevance=_clean_list(payload.product_relevance),
            created_at=now,
            updated_at=now,
        )
        self.repository.add(source)
        self._add_audit("source_created", source, None, _state(source))
        self.session.commit()
        self.session.refresh(source)
        return source

    def update_source(self, source_id: str, payload: SourceUpdate) -> Source:
        source = self._get_required(source_id)
        before_state = _state(source)
        updates = payload.model_dump(exclude_unset=True)
        for field in ("name", "source_type"):
            if field in updates:
                setattr(source, field, _required_text(updates[field], f"Source {field}"))
        if "domain" in updates:
            source.domain = _clean_text(updates["domain"])
        if "country" in updates:
            source.country = updates["country"].strip().upper() if updates["country"] else None
        for field in ("access_method", "operational_status", "reliability_score", "last_checked_at"):
            if field in updates:
                setattr(source, field, updates[field])
        if "notes" in updates:
            source.notes = _clean_text(updates["notes"])
        if "product_relevance" in updates:
            source.product_relevance = _clean_list(updates["product_relevance"])

        source.updated_at = utc_now()
        action = "source_updated"
        if before_state["operational_status"] != source.operational_status.value:
            action = "source_operational_status_changed"
        self._add_audit(action, source, before_state, _state(source))
        self.session.commit()
        self.session.refresh(source)
        return source

    def approve_source(self, source_id: str) -> Source:
        source = self._get_required(source_id)
        if source.approval_status is not SourceApprovalStatus.CANDIDATE:
            raise InvalidConfigurationTransition(
                f"Invalid source approval transition: {source.approval_status.value} -> approved"
            )
        return self._approval_transition(source, SourceApprovalStatus.APPROVED, "source_approved")

    def reject_source(self, source_id: str) -> Source:
        source = self._get_required(source_id)
        if source.approval_status is not SourceApprovalStatus.CANDIDATE:
            raise InvalidConfigurationTransition(
                f"Invalid source approval transition: {source.approval_status.value} -> rejected"
            )
        return self._approval_transition(source, SourceApprovalStatus.REJECTED, "source_rejected")

    def list_sources(
        self,
        *,
        limit: int,
        offset: int,
        approval_status: SourceApprovalStatus | None = None,
        operational_status: SourceOperationalStatus | None = None,
    ) -> list[Source]:
        return self.repository.list(
            limit=min(max(limit, 1), 100),
            offset=max(offset, 0),
            approval_status=approval_status,
            operational_status=operational_status,
        )

    def list_eligible_sources(self, *, limit: int, offset: int) -> list[Source]:
        return self.repository.list_eligible(limit=min(max(limit, 1), 100), offset=max(offset, 0))

    def get_source(self, source_id: str) -> Source | None:
        return self.repository.get(source_id)

    def _get_required(self, source_id: str) -> Source:
        source = self.repository.get(source_id)
        if source is None:
            raise ConfigurationNotFoundError(source_id)
        return source

    def _approval_transition(self, source: Source, status: SourceApprovalStatus, action: str) -> Source:
        before_state = _state(source)
        source.approval_status = status
        source.updated_at = utc_now()
        self._add_audit(action, source, before_state, _state(source))
        self.session.commit()
        self.session.refresh(source)
        return source

    def _add_audit(
        self,
        action: str,
        source: Source,
        before_state: dict[str, Any] | None,
        after_state: dict[str, Any] | None,
    ) -> None:
        self.session.add(
            AuditEvent(
                audit_id=make_id("AUD"),
                actor_type="system",
                actor_id="configuration_service",
                action=action,
                entity_type="source",
                entity_id=source.source_id,
                before_state=before_state,
                after_state=after_state,
                timestamp=utc_now(),
            )
        )
