# Aeropex Buyer Intelligence Data Platform

## Data Contracts V0.1

**Document Type:** Data Contract Specification  
**Version:** 0.1  
**Status:** Architecture Baseline  
**Platform:** Aeropex Buyer Intelligence Data Platform

---

## 1. Purpose

This document defines the shared data contracts used across the Aeropex Buyer Intelligence Data Platform.

These contracts establish how data is exchanged between:

- Aeropex Control Panel
- FastAPI Backend
- PostgreSQL
- Redis / Celery
- Agent Services
- Buyer Discovery
- Source Registry
- ADLS Gen2
- Azure Data Factory
- Databricks / PySpark
- Verification and Research
- Matching
- Outreach
- Human Approval workflows

All services must use defined contracts rather than passing arbitrary or undocumented data structures.

---

## 2. Core Data Contract Principles

The following rules apply across the platform.

1. IDs must be unique and stable.
2. Timestamps must use UTC ISO-8601 format.
3. Raw source observations are immutable.
4. Unknown information must remain `null`.
5. Missing information must never be fabricated.
6. Original source evidence must be retained.
7. Important records must be traceable to their source.
8. AI-generated structured output must pass schema validation.
9. Observed, inferred, and verified information must remain distinguishable.
10. Contracts must support versioning.
11. Services communicate through explicit schemas.
12. Important system actions must be auditable.
13. Partial records may be retained when commercially useful.
14. Data-quality problems should be flagged rather than silently discarded.

---

# 3. Common Enumerations

## 3.1 AgentStatus

```text
active
idle
running
degraded
failed
disabled
```

---

## 3.2 RunStatus

```text
queued
running
completed
completed_with_warnings
failed
cancelled
```

---

## 3.3 TriggerType

```text
manual
scheduled
event
retry
system
```

---

## 3.4 AuthorityLevel

```text
green
yellow
red
```

### Green

System may execute autonomously.

### Yellow

System may analyze, recommend, or draft, but human approval is required before consequential action.

### Red

Human-only decision or action.

---

## 3.5 VerificationStatus

```text
unverified
pending
partially_verified
verified
rejected
```

---

## 3.6 ApprovalStatus

```text
pending
approved
rejected
cancelled
expired
```

---

## 3.7 SourceApprovalStatus

```text
candidate
approved
rejected
```

---

## 3.8 SourceOperationalStatus

```text
active
degraded
disabled
unavailable
```

---

## 3.9 SourceAccessMethod

```text
api
http
browser
manual
```

Connectors are not implemented in M2.1. The access method records governed metadata only.

---

## 3.10 ErrorSeverity

```text
info
warning
error
critical
```

---

# 4. Agent Contract

Represents a bounded AI agent or platform worker capability.

## Example

```json
{
  "agent_id": "AGT-BUYER-DISCOVERY-001",
  "name": "Buyer Discovery",
  "type": "buyer_discovery",
  "status": "active",
  "version": "0.1.0",
  "capabilities": [
    "source_selection",
    "buyer_opportunity_discovery",
    "evidence_capture"
  ],
  "authority_level": "green",
  "last_heartbeat_at": "2026-09-12T01:30:00Z",
  "created_at": "2026-09-12T00:00:00Z",
  "updated_at": "2026-09-12T01:30:00Z"
}
```

## Required Fields

| Field | Type |
|---|---|
| `agent_id` | string |
| `name` | string |
| `type` | string |
| `status` | AgentStatus |
| `version` | string |
| `authority_level` | AuthorityLevel |
| `created_at` | datetime |
| `updated_at` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `capabilities` | array[string] |
| `last_heartbeat_at` | datetime / null |

---

# 5. AgentRun Contract

Represents one execution of an agent or worker.

## Example

```json
{
  "run_id": "RUN-20260912-000001",
  "agent_id": "AGT-BUYER-DISCOVERY-001",
  "trigger_type": "manual",
  "status": "completed",
  "started_at": "2026-09-12T01:00:00Z",
  "finished_at": "2026-09-12T01:04:28Z",
  "records_processed": 22,
  "records_created": 6,
  "retry_count": 0,
  "error_count": 1,
  "summary": "Checked 4 sources and discovered 6 candidate buyer opportunities."
}
```

## Required Fields

| Field | Type |
|---|---|
| `run_id` | string |
| `agent_id` | string |
| `trigger_type` | TriggerType |
| `status` | RunStatus |
| `started_at` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `finished_at` | datetime / null |
| `records_processed` | integer >= 0 |
| `records_created` | integer >= 0 |
| `retry_count` | integer >= 0 |
| `error_count` | integer >= 0 |
| `summary` | string / null |

---

# 6. Source Contract

Represents a source available to the discovery platform.

## Example

```json
{
  "source_id": "SRC-0001",
  "name": "Example Trade Portal",
  "domain": "example.com",
  "country": "AE",
  "source_type": "trade_portal",
  "access_method": "http",
  "approval_status": "candidate",
  "operational_status": "active",
  "reliability_score": null,
  "last_checked_at": null,
  "notes": "Candidate source awaiting human review.",
  "product_relevance": [],
  "created_at": "2026-09-12T00:00:00Z",
  "updated_at": "2026-09-12T00:00:00Z"
}
```

## Required Fields

| Field | Type |
|---|---|
| `source_id` | string |
| `name` | string |
| `source_type` | string |
| `access_method` | SourceAccessMethod |
| `approval_status` | SourceApprovalStatus |
| `operational_status` | SourceOperationalStatus |
| `created_at` | datetime |
| `updated_at` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `domain` | string / null |
| `country` | ISO country code / null |
| `reliability_score` | decimal 0.0–1.0 / null |
| `last_checked_at` | datetime / null |
| `notes` | string / null |
| `product_relevance` | array[string] |

## Governance Rules

New sources start as `candidate`. Human-controlled lifecycle actions may transition:

```text
candidate -> approved
candidate -> rejected
```

The reusable eligibility rule for future Buyer Discovery is:

```text
approval_status == approved
AND
operational_status == active
```

Approval status and operational status are independent; an approved source may still be degraded, disabled, or unavailable.

---

# 7. Product Contract

Represents a configurable Aeropex product definition.

Products must be configuration-driven and must not be hard-coded into individual agents.

## Example

```json
{
  "product_id": "PRD-RED-CHILLI",
  "category": "spices",
  "name": "Red Chilli",
  "aliases": [
    "red chili"
  ],
  "variants": [],
  "hs_codes": [],
  "priority": 1,
  "active": true,
  "created_at": "2026-09-12T00:00:00Z",
  "updated_at": "2026-09-12T00:00:00Z"
}
```

## Required Fields

| Field | Type |
|---|---|
| `product_id` | string |
| `category` | string |
| `name` | string |
| `active` | boolean |
| `created_at` | datetime |
| `updated_at` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `aliases` | array[string] |
| `variants` | array[string] |
| `hs_codes` | array[string] |
| `priority` | integer / null |

## Configuration Rules

Products are platform-owned configuration entities. Product names and categories are required, list fields may be empty, and unknown HS codes must remain absent rather than fabricated. Product lifecycle should prefer `active=false` over destructive deletion so historical references remain stable.

---

# 8. Buyer Contract

Represents a normalized buyer organization.

A Buyer is a business entity.

A source observation does **not** automatically become a Buyer.

Buyer creation or linking occurs during normalization and entity-resolution processing.

## Example

```json
{
  "buyer_id": "BUY-000001",
  "company_name": "ABC Foods LLC",
  "country": "AE",
  "website": "https://example.com",
  "company_type": "importer_distributor",
  "verification_status": "unverified",
  "confidence_score": 0.71,
  "created_at": "2026-09-12T01:10:00Z",
  "updated_at": "2026-09-12T01:10:00Z"
}
```

## Required Fields

| Field | Type |
|---|---|
| `buyer_id` | string |
| `company_name` | string |
| `verification_status` | VerificationStatus |
| `created_at` | datetime |
| `updated_at` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `country` | ISO country code / null |
| `website` | URL / null |
| `company_type` | string / null |
| `confidence_score` | decimal 0.0–1.0 / null |

---

# 9. BuyerRequirement Contract

Represents a commercial requirement associated with a Buyer.

One Buyer may have multiple BuyerRequirements.

## Example

```json
{
  "requirement_id": "REQ-000001",
  "buyer_id": "BUY-000001",
  "product_id": "PRD-RED-CHILLI",
  "requirement_text": "Seeking dried red chilli for monthly import.",
  "quantity": 20,
  "unit": "metric_ton",
  "specifications": {
    "form": "whole",
    "moisture_max_pct": 12
  },
  "destination": "Jebel Ali, UAE",
  "posted_at": "2026-09-10T09:00:00Z",
  "status": "open"
}
```

## Required Fields

| Field | Type |
|---|---|
| `requirement_id` | string |
| `buyer_id` | string |
| `product_id` | string |
| `requirement_text` | string |
| `status` | string |

## Optional Fields

| Field | Type |
|---|---|
| `quantity` | decimal / null |
| `unit` | string / null |
| `specifications` | object |
| `destination` | string / null |
| `posted_at` | datetime / null |

---

# 10. SourceObservation Contract

Represents the immutable raw evidence discovered from an external source.

This is one of the most important contracts in the platform.

The SourceObservation preserves what the system actually observed before normalization, verification, enrichment, or matching occurs.

## Example

```json
{
  "observation_id": "OBS-000001",
  "source_id": "SRC-0001",
  "run_id": "RUN-20260912-000001",
  "buyer_id": null,
  "requirement_id": null,
  "source_url": "https://example.com/rfq/123",
  "raw_text": "Looking to import dried red chilli...",
  "evidence_type": "public_rfq",
  "captured_at": "2026-09-12T01:02:14Z",
  "confidence_score": 0.87
}
```

## Required Fields

| Field | Type |
|---|---|
| `observation_id` | string |
| `source_id` | string |
| `run_id` | string |
| `captured_at` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `buyer_id` | string / null |
| `requirement_id` | string / null |
| `source_url` | URL / null |
| `raw_text` | string / null |
| `evidence_type` | string / null |
| `confidence_score` | decimal 0.0–1.0 / null |

## Immutability Rule

`SourceObservation` records must never be overwritten simply because later research discovers better information.

Example:

```text
Source says:
ABC Food Trading

Later verification determines:
ABC Food Trading LLC
```

The original SourceObservation remains:

```text
ABC Food Trading
```

The normalized Buyer may become:

```text
ABC Food Trading LLC
```

This preserves lineage.

---

# 11. ErrorEvent Contract

Represents a warning or failure occurring during platform execution.

## Example

```json
{
  "error_id": "ERR-000001",
  "run_id": "RUN-20260912-000001",
  "agent_id": "AGT-BUYER-DISCOVERY-001",
  "error_type": "source_timeout",
  "severity": "warning",
  "message": "Source did not respond before timeout.",
  "retryable": true,
  "resolved": false,
  "created_at": "2026-09-12T01:03:10Z"
}
```

## Required Fields

| Field | Type |
|---|---|
| `error_id` | string |
| `error_type` | string |
| `severity` | ErrorSeverity |
| `message` | string |
| `retryable` | boolean |
| `resolved` | boolean |
| `created_at` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `run_id` | string / null |
| `agent_id` | string / null |

---

# 12. Approval Contract

Represents an action requiring human authorization.

This contract implements the Yellow and Red authority boundaries defined in the platform requirements.

## Example

```json
{
  "approval_id": "APR-000001",
  "entity_type": "outreach_draft",
  "entity_id": "OUT-000001",
  "action_type": "send_email",
  "requested_by": "AGT-OUTREACH-001",
  "status": "pending",
  "approved_by": null,
  "created_at": "2026-09-12T01:20:00Z",
  "resolved_at": null
}
```

## Required Fields

| Field | Type |
|---|---|
| `approval_id` | string |
| `entity_type` | string |
| `entity_id` | string |
| `action_type` | string |
| `requested_by` | string |
| `status` | ApprovalStatus |
| `created_at` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `approved_by` | string / null |
| `resolved_at` | datetime / null |

---

# 13. AuditEvent Contract

Represents an auditable action performed by a human, service, or agent.

## Example

```json
{
  "audit_id": "AUD-000001",
  "actor_type": "agent",
  "actor_id": "AGT-BUYER-DISCOVERY-001",
  "action": "captured_source_observation",
  "entity_type": "source_observation",
  "entity_id": "OBS-000001",
  "before_state": null,
  "after_state": {
    "status": "captured"
  },
  "timestamp": "2026-09-12T01:02:15Z"
}
```

## Required Fields

| Field | Type |
|---|---|
| `audit_id` | string |
| `actor_type` | string |
| `actor_id` | string |
| `action` | string |
| `entity_type` | string |
| `entity_id` | string |
| `timestamp` | datetime |

## Optional Fields

| Field | Type |
|---|---|
| `before_state` | object / null |
| `after_state` | object / null |

---

# 14. Core Relationship Model

```text
Product
   |
   |
Source Registry
   |
   v
Buyer Discovery Agent
   |
   v
AgentRun
   |
   v
SourceObservation
   |
   | Normalization / Entity Resolution
   |
   +--------------------+
   |                    |
   v                    v
Buyer             BuyerRequirement
   |                    |
   +---------+----------+
             |
             v
      Future Verification
             |
             v
       Future Matching
             |
             v
       Future Outreach
```

Operational governance:

```text
Agent
  |
  +---- AgentRun
  |
  +---- ErrorEvent
  |
  +---- AuditEvent

Approval
  |
  +---- Governed Business Action
```

---

# 15. Bronze Data Rule

The initial discovery flow must follow:

```text
External Source
      |
      v
Source Connector
      |
      v
Raw Observation
      |
      v
Schema Validation
      |
      v
SourceObservation
      |
      v
ADLS Gen2
      |
      v
BRONZE
```

Buyer Discovery must **not** directly assume that every discovered record represents a unique Buyer.

Normalization occurs downstream.

---

# 16. Information Confidence Model

The platform must distinguish three information states.

## Observed

Information directly present in original source evidence.

Example:

```text
"We require 20 MT of dried red chilli."
```

---

## Inferred

Information derived by software or AI but not independently verified.

Example:

```text
The organization appears to be an importer/distributor.
```

---

## Verified

Information confirmed through reliable supporting evidence.

Example:

```text
Company identity verified against official company information.
```

AI inference must never automatically become verified information.

---

# 17. Null Handling

Unknown information must remain:

```json
null
```

Do not generate placeholder values such as:

```text
Unknown Company
N/A Buyer
Probably UAE
Likely Procurement Manager
```

unless those values are explicitly presentation labels and not stored as facts.

Example:

```json
{
  "contact_name": null,
  "contact_email": null,
  "quantity": null
}
```

is valid.

---

# 18. Data Lineage

Every important discovery should eventually support lineage similar to:

```text
BUY-000001
    |
REQ-000001
    |
OBS-000001
    |
SRC-0001
    |
RUN-20260912-000001
    |
AGT-BUYER-DISCOVERY-001
```

This allows Aeropex to answer:

```text
Who discovered this?

When was it discovered?

Where was it discovered?

What did the original source say?

Which agent run captured it?

What transformations occurred?

Was it verified?

What happened afterward?
```

---

# 19. V0.1 Contract Rules

The following rules are locked for V0.1.

1. Raw observations are immutable.
2. IDs remain stable after creation.
3. Timestamps use UTC.
4. Optional information remains nullable.
5. Missing information is never fabricated.
6. AI output must pass schema validation.
7. One Buyer may have multiple BuyerRequirements.
8. One BuyerRequirement may have multiple SourceObservations.
9. Multiple SourceObservations may resolve to one Buyer.
10. Every consequential action should be auditable.
11. Raw evidence must be retained where appropriate.
12. Discovery and verification remain separate.
13. Discovery and matching remain separate.
14. Discovery and outreach remain separate.
15. SourceObservation precedes normalized Buyer creation.
16. Entity resolution occurs downstream.
17. Data-quality failures must not silently destroy evidence.

---

# 20. Deferred Data Contracts

The following contracts are intentionally deferred until their workflows are designed.

## Supplier Domain

```text
Supplier
SupplierProduct
SupplierCapability
SupplierCertification
```

## Network Domain

```text
TradeIntermediary
Contact
RelationshipEvent
```

## Intelligence Domain

```text
VerificationResult
EnrichmentResult
Match
MatchExplanation
```

## Commercial Domain

```text
RFQ
OutreachDraft
OutreachEvent
Quotation
```

## Platform Domain

```text
Notification
SupervisorDecision
WorkflowEvent
SourceHealthEvent
```

These contracts should not be prematurely designed before their workflow requirements are understood.

---

# 21. V0.1 Data Flow

```text
                    PRODUCT CONFIGURATION
                            |
                            v
                       SOURCE REGISTRY
                            |
                            v
                    BUYER DISCOVERY
                            |
                            v
                       AGENT RUN
                            |
                            v
                     SOURCE CONNECTOR
                            |
                            v
                      RAW EVIDENCE
                            |
                            v
                    SCHEMA VALIDATION
                            |
                            v
                   SOURCE OBSERVATION
                            |
                +-----------+-----------+
                |                       |
                v                       v
          PostgreSQL                 ADLS Gen2
       Operational State              BRONZE
                                        |
                                        v
                                      ADF
                                        |
                                        v
                                  DATABRICKS
                                    PYSPARK
                                        |
                                        v
                                     SILVER
                                        |
                              Entity Resolution
                              Standardization
                              Deduplication
                              Data Quality
                                        |
                                        v
                                      GOLD
                                        |
                                        v
                            Future Intelligence Layer
```

---

# 22. Technology Mapping

| Contract | Primary Storage / Processing |
|---|---|
| Agent | PostgreSQL |
| AgentRun | PostgreSQL |
| Source | PostgreSQL |
| Product | PostgreSQL |
| SourceObservation metadata | PostgreSQL |
| Raw SourceObservation evidence | ADLS Gen2 Bronze |
| Buyer | PostgreSQL / Curated Data Layer |
| BuyerRequirement | PostgreSQL / Curated Data Layer |
| ErrorEvent | PostgreSQL |
| Approval | PostgreSQL |
| AuditEvent | PostgreSQL |
| Analytical datasets | Delta Lake |
| Silver datasets | Delta Lake |
| Gold datasets | Delta Lake |

Exact physical implementation may evolve during detailed architecture.

---

# 23. Contract Versioning

Contracts must support future evolution.

Initial contract version:

```text
v0.1
```

Breaking changes require an explicit version change.

Example:

```text
v0.1
v0.2
v1.0
```

Services must not silently introduce breaking schema changes.

---

# 24. Validation Strategy

Application contracts will eventually be implemented using:

```text
Python
+
Pydantic
```

Persistence models will use:

```text
PostgreSQL
+
SQLAlchemy
```

Validation tests must verify:

- Required fields
- Enum values
- Null handling
- URL validation
- Timestamp validation
- Confidence score boundaries
- Referential relationships
- Invalid payload rejection
- Schema serialization/deserialization

---

# 25. Next Engineering Step

After this document is reviewed and committed:

```text
Requirements
      ✓
Architecture Decisions
      ✓
Data Contracts V0.1
      ✓
      |
      v
Repository Structure
      |
      v
FastAPI Skeleton
      |
      v
Pydantic Models
      |
      v
PostgreSQL Models
      |
      v
Redis / Celery
      |
      v
Automated Tests
      |
      v
Control Panel V0.1
      |
      v
Buyer Discovery V0.1
```

No buyer scraping or AI-agent implementation should begin until the foundational application contracts are implemented and tested.

---

# 26. Current Status

**Requirements:** Baseline Complete  
**Architecture:** V0.1 Baseline Defined  
**Data Contracts:** V0.1 Defined  
**Implementation:** Not Started

---

# 27. Next Milestone

## Milestone M1 — Platform Foundation

M1 will establish the minimum production-oriented application foundation.

Expected components:

- Repository structure
- FastAPI backend
- Pydantic contracts
- PostgreSQL integration
- Redis integration
- Celery worker
- Configuration management
- Structured logging
- Health checks
- Initial automated tests
- Development environment
- Initial Next.js control-panel shell

Buyer Discovery will be implemented only after M1 foundation tests pass.

---

# 28. Change Log

## V0.1

Initial Aeropex Buyer Intelligence Platform data-contract baseline.

Defined:

- Agent
- AgentRun
- Source
- Product
- Buyer
- BuyerRequirement
- SourceObservation
- ErrorEvent
- Approval
- AuditEvent
- Core enumerations
- Immutability rules
- Evidence handling
- Null handling
- Confidence model
- Lineage requirements
- Bronze ingestion boundary
- Technology mapping
- Contract versioning
- Validation strategy

## M1.2 Operational Persistence & Run Lifecycle

Implemented the first operational persistence subset in PostgreSQL:

- Agent
- AgentRun
- ErrorEvent
- AuditEvent

Run lifecycle state changes are handled through a bounded service, with M1.2 transitions limited to:

- queued -> running
- queued -> cancelled
- running -> completed
- running -> completed_with_warnings
- running -> failed
- running -> cancelled

Terminal run states remain terminal. The initial Buyer Discovery agent is registered for operational testing only; actual Buyer Discovery remains deferred.

## M1.3 Control Panel Operational Dashboard

Implemented the first functional Aeropex Control Panel using the existing M1.2 operational contracts:

- Agent
- AgentRun
- ErrorEvent

Added API presentation support for bounded error listing, operational summary counts, and agent-filtered run listing. No new buyer, supplier, source observation, matching, outreach, or approval contracts were introduced in this milestone.

Buyer Discovery remains registered for operational testing only; actual buyer discovery and source collection remain deferred.

## M2.1 Product Configuration & Source Registry

Implemented platform-owned configuration contracts and persistence for:

- `ProductCreate`, `ProductUpdate`, `ProductRead`
- `SourceCreate`, `SourceUpdate`, `SourceRead`
- `SourceAccessMethod`

Products and sources are governed control-plane data exposed through FastAPI and the Control Panel. Buyer Discovery may consume approved configuration in later milestones, but it does not own or arbitrarily mutate production product/source configuration.

M2.1 explicitly does not implement source connectors, buyer scraping, browser automation, AI extraction, buyer matching, verification, outreach, ADLS ingestion, ADF, Databricks, or scheduled discovery execution.
