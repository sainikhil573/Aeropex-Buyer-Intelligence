"""Repositories for platform-owned configuration entities."""

from __future__ import annotations

from aeropex_contracts.enums import SourceApprovalStatus, SourceOperationalStatus
from sqlalchemy.orm import Session

from aeropex_api.db.models import Product, Source


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, product_id: str) -> Product | None:
        return self.session.get(Product, product_id)

    def add(self, product: Product) -> Product:
        self.session.add(product)
        return product

    def list(self, *, limit: int, offset: int, active: bool | None = None, category: str | None = None) -> list[Product]:
        query = self.session.query(Product)
        if active is not None:
            query = query.filter(Product.active == active)
        if category:
            query = query.filter(Product.category == category)
        return query.order_by(Product.priority.asc(), Product.name.asc()).offset(offset).limit(limit).all()

    def active_name_exists(self, *, name: str, excluding_product_id: str | None = None) -> bool:
        query = self.session.query(Product).filter(Product.active.is_(True), Product.name == name)
        if excluding_product_id:
            query = query.filter(Product.product_id != excluding_product_id)
        return self.session.query(query.exists()).scalar() is True


class SourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, source_id: str) -> Source | None:
        return self.session.get(Source, source_id)

    def add(self, source: Source) -> Source:
        self.session.add(source)
        return source

    def list(
        self,
        *,
        limit: int,
        offset: int,
        approval_status: SourceApprovalStatus | None = None,
        operational_status: SourceOperationalStatus | None = None,
    ) -> list[Source]:
        query = self.session.query(Source)
        if approval_status is not None:
            query = query.filter(Source.approval_status == approval_status)
        if operational_status is not None:
            query = query.filter(Source.operational_status == operational_status)
        return query.order_by(Source.name.asc()).offset(offset).limit(limit).all()

    def list_eligible(self, *, limit: int, offset: int) -> list[Source]:
        return self.list(
            limit=limit,
            offset=offset,
            approval_status=SourceApprovalStatus.APPROVED,
            operational_status=SourceOperationalStatus.ACTIVE,
        )
