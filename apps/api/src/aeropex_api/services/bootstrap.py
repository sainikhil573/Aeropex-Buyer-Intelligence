"""Safe bootstrap helpers for operational reference data."""

from __future__ import annotations

from datetime import UTC, datetime

from aeropex_contracts.enums import (
    AgentStatus,
    AuthorityLevel,
    SourceAccessMethod,
    SourceOperationalStatus,
)
from aeropex_contracts.models import ProductCreate, SourceCreate
from sqlalchemy.orm import Session

from aeropex_api.db.models import Agent
from aeropex_api.services.configuration import ProductService, SourceService

BUYER_DISCOVERY_AGENT_ID = "AGT-BUYER-DISCOVERY-001"


def bootstrap_initial_agents(session: Session) -> Agent:
    """Register the initial operational agent in an idempotent way."""

    agent = session.get(Agent, BUYER_DISCOVERY_AGENT_ID)
    now = datetime.now(UTC)
    if agent is None:
        agent = Agent(
            agent_id=BUYER_DISCOVERY_AGENT_ID,
            name="Buyer Discovery",
            type="buyer_discovery",
            status=AgentStatus.ACTIVE,
            version="0.1.0",
            capabilities=[],
            authority_level=AuthorityLevel.GREEN,
            last_heartbeat_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
    return agent


def bootstrap_initial_products(session: Session) -> None:
    """Seed the initial product catalog in an idempotent way."""

    service = ProductService(session)
    products = [
        ("PRD-RED-CHILLI", "Red Chilli", 10),
        ("PRD-TURMERIC", "Turmeric", 20),
        ("PRD-BLACK-PEPPER", "Black Pepper", 30),
        ("PRD-CUMIN", "Cumin", 40),
        ("PRD-CORIANDER", "Coriander", 50),
        ("PRD-CARDAMOM", "Cardamom", 60),
    ]
    for product_id, name, priority in products:
        if service.get_product(product_id) is None:
            service.create_product(
                ProductCreate(
                    product_id=product_id,
                    category="Spices",
                    name=name,
                    aliases=[],
                    variants=[],
                    hs_codes=[],
                    priority=priority,
                    active=True,
                )
            )


def bootstrap_initial_sources(session: Session) -> None:
    """Seed candidate source registry examples without claiming approval."""

    service = SourceService(session)
    sources = [
        SourceCreate(
            source_id="SRC-TRADE-PORTAL-CANDIDATE",
            name="Trade Portal Candidate",
            domain="example-trade.invalid",
            source_type="trade_portal",
            access_method=SourceAccessMethod.HTTP,
            operational_status=SourceOperationalStatus.ACTIVE,
            notes="Placeholder registry candidate; no connector implemented.",
        ),
        SourceCreate(
            source_id="SRC-MANUAL-RESEARCH-CANDIDATE",
            name="Manual Research Candidate",
            source_type="manual_research",
            access_method=SourceAccessMethod.MANUAL,
            operational_status=SourceOperationalStatus.ACTIVE,
            notes="Placeholder for governed source intake.",
        ),
        SourceCreate(
            source_id="SRC-PUBLIC-DIRECTORY-CANDIDATE",
            name="Public Directory Candidate",
            domain="example-directory.invalid",
            source_type="directory",
            access_method=SourceAccessMethod.HTTP,
            operational_status=SourceOperationalStatus.ACTIVE,
            notes="Candidate registry metadata only.",
        ),
    ]
    for source in sources:
        if service.get_source(source.source_id) is None:
            service.create_source(source)


def bootstrap_configuration(session: Session) -> None:
    """Seed all M2.1 configuration domains idempotently."""

    bootstrap_initial_products(session)
    bootstrap_initial_sources(session)
