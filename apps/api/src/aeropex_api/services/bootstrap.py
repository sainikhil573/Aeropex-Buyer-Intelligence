"""Safe bootstrap helpers for operational reference data."""

from __future__ import annotations

from datetime import UTC, datetime

from aeropex_contracts.enums import AgentStatus, AuthorityLevel
from sqlalchemy.orm import Session

from aeropex_api.db.models import Agent

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
