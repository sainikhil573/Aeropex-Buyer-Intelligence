# ADR-015 - Product and Source Configuration Ownership

## Status

Accepted

## Context

Buyer Discovery requires product definitions and source registry metadata, but those entities affect platform behavior beyond any single discovery run. Allowing an agent to freely create or mutate production product/source configuration would make discovery behavior harder to audit and govern.

## Decision

Product Configuration and Source Registry are platform-owned control-plane data.

Buyer Discovery may consume approved configuration in later milestones, but it does not own or arbitrarily mutate production product/source configuration during discovery runs.

Configuration changes flow through:

```text
Control Panel
  -> FastAPI
  -> Application Service Layer
  -> Repository/Persistence Layer
  -> PostgreSQL
```

Source approval is explicit and human-controlled. A source is eligible for future Buyer Discovery only when:

```text
approval_status == approved
AND
operational_status == active
```

## Consequences

- Products and sources can be audited independently of discovery execution.
- Source approval and operational state remain separate.
- Buyer Discovery implementation can stay data-driven without hard-coded product/source logic.
- M2.1 intentionally does not implement connectors, scraping, browser automation, AI extraction, matching, verification, outreach, or scheduled discovery execution.
