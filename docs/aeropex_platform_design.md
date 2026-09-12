# Aeropex Buyer Intelligence Data Platform

**Document Type:** Product Requirements & Platform Design  
**Version:** 0.1  
**Status:** Requirements Baseline  
**Last Updated:** September 10, 2026

---

## 1. Purpose

Aeropex Buyer Intelligence Data Platform is an internal AI-assisted
data and operations platform for Aeropex Exports.

The platform will discover global trade opportunities, collect buyer,
supplier, and intermediary information, transform fragmented source
data into trusted business-ready datasets, verify and enrich records,
match buyer requirements with supplier capabilities, and support
outreach and commercial decision-making.

The platform is designed around one principle:

> AI may automate research and operations, but consequential commercial,
> financial, and legal decisions remain under human control.

---

## 2. Business Problem

Buyer and supplier intelligence is currently fragmented across trade
portals, company websites, professional networks, direct contacts,
offline relationships, and other sources.

This creates several problems:

- Buyer opportunities can be missed.
- Research requires significant manual effort.
- Contact information may be incomplete.
- Duplicate companies may appear across multiple sources.
- Supplier information may be incomplete or inconsistent.
- Buyer requirements are difficult to compare with supplier capabilities.
- Original source evidence can be lost.
- Follow-ups and relationship history are difficult to track.
- There is limited visibility into automated workflows and failures.
- Scaling research across products and countries requires excessive
  manual effort.

The platform should convert this fragmented information into a
traceable and actionable intelligence system.

---

## 3. Initial Users

### V0.1

Primary user:

- Aeropex platform administrator / business operator

### Future

The architecture should support additional users such as:

- Co-founder
- Operations team members
- Sales/business-development users
- Analysts
- Administrators

Future versions should implement Role-Based Access Control (RBAC).

Potential roles may include:

- Administrator
- Operator
- Viewer
- Approver

RBAC is not required for the first implementation but the architecture
must not prevent its introduction later.

---

# 4. Functional Requirements

## FR-001 — Unified Operational Visibility & Control

The platform shall provide an Aeropex Control Panel that acts as the
operational interface for the intelligence platform.

The user should be able to view:

- Registered agents/services
- Agent status
- Running, idle, degraded, failed, or disabled state
- Assigned responsibilities
- Last execution time
- Current/most recent execution
- Number of records discovered
- Number of successful and failed operations
- Recent activity
- Errors and warnings
- Operational logs
- Data pipeline status
- Records awaiting verification
- Records awaiting human approval
- Data-quality indicators
- Supervisor activity
- Recent buyer/supplier activity

High-priority events should be surfaced prominently, including:

- New RFQs
- Buyer responses
- Supplier responses
- Critical system failures
- High-priority opportunities
- Items requiring human approval

The interface should eventually support search and filtering across
agents, leads, sources, logs, and operational events.

The Control Panel is an operations console, not merely a visualization
dashboard.

---

## FR-002 — Multi-Channel Data Ingestion

The platform shall support data entering from multiple channels.

Initial channels include:

- Automated buyer discovery
- Automated supplier discovery
- Manual entry

Future channels may include:

- APIs
- Files
- Email
- Webhooks
- Partner systems
- Bulk imports

Manual entry shall be treated as a first-class ingestion mechanism.

Users should eventually be able to manually create records for:

- Buyers
- Suppliers
- Trade intermediaries
- Business contacts
- Requirements/opportunities

All records should enter the common data platform regardless of their
source.

---

## FR-003 — Entity-Specific Data Quality

Different business entities shall have different validation and
completeness requirements.

Initial entity types include:

- Buyer
- Supplier
- Trade intermediary
- Contact
- Buyer requirement
- Product
- Source
- Source observation

Incomplete records shall not automatically be discarded.

Missing information should be represented explicitly as unknown,
unavailable, or requiring enrichment.

The platform should track:

- Record completeness
- Validation status
- Verification status
- Data-quality issues
- Missing critical fields

Example:

An offline trade intermediary with only a name, phone number, country,
and product interest may still be valuable and should remain in the
platform.

---

## FR-004 — Configurable Product Discovery & Trade Classification

Product discovery logic shall be configuration-driven rather than
hard-coded.

Initial category:

**Spices**

Individual products may include:

- Red chilli
- Turmeric
- Black pepper
- Cumin
- Coriander
- Cardamom
- Additional products added later

Each product definition should eventually support:

- Product ID
- Product name
- Category
- Product aliases
- Common spelling variations
- Product variants
- Whole/powder/processed form
- Relevant HS code(s)
- Search terminology
- Buyer-intent terminology
- Priority
- Active/inactive status

HS codes shall be maintained as structured reference data rather than
embedded directly into agent logic.

The architecture should allow a new product to be activated primarily
through configuration rather than application code changes.

---

## FR-005 — Dynamic Source Discovery & Governance

The platform shall maintain a Source Registry describing sources that
may be used for discovery.

Sources may include:

- Public trade portals
- Procurement/tender portals
- Government/public trade resources
- Company websites
- Business directories
- Public professional/business information
- Other legitimate sources

The system may discover and propose new sources automatically.

However, newly discovered sources shall not automatically become
trusted production sources.

Initial governance model:

1. System discovers candidate source.
2. Candidate is recorded.
3. Source is classified.
4. Access constraints are evaluated.
5. Human reviews the source.
6. Human approves or rejects it.
7. Approved source becomes active.

Source metadata should eventually include:

- Source ID
- Source name
- URL/domain
- Country/region
- Source type
- Product relevance
- Access type
- Authentication requirement
- Collection method
- Reliability rating
- Last successful check
- Operational status
- Approval status

The platform shall respect applicable access restrictions and shall not
attempt to bypass authentication, technical controls, or source
restrictions.

---

## FR-006 — Buyer & Contact Enrichment

Discovery and enrichment shall remain separate responsibilities.

Buyer Discovery should first preserve the opportunity and its original
evidence.

If important information is missing, an enrichment/research capability
may attempt to identify additional publicly available business
information.

Enrichment may include:

- Company website
- Company identity
- Relevant business activity
- Public business email
- Public business phone
- Procurement/sourcing contacts
- Relevant professional profiles
- Country/location
- Product relevance
- Additional requirement context

Every enrichment result should include:

- Source/evidence
- Timestamp
- Confidence level
- Verification state

The system must distinguish:

**Observed fact → Inferred information → Verified information**

The platform must not silently convert an inference into a verified
fact.

---

## FR-007 — Multi-Mode Workflow Execution

The platform shall eventually support three execution modes.

### Scheduled Execution

Used for recurring monitoring such as:

- Buyer discovery
- Supplier discovery
- Source health checks
- Periodic enrichment

Schedules should be configurable.

### Manual Execution

The Control Panel should provide authorized users with the ability to
initiate supported workflows manually.

Example:

**Run Buyer Discovery Now**

### Event-Driven Execution

Events should trigger downstream work where appropriate.

Example:

New buyer requirement
→ enrichment task
→ verification
→ matching
→ human review

For V0.1, implementation may begin with scheduled execution, manual
execution, and basic internal event creation.

---

## FR-008 — Resilient Failure Handling & Recovery

The platform shall classify and respond to failures based on failure
type.

### Temporary Failures

Examples:

- Network timeout
- Temporary API failure
- Service unavailable

Response:

- Retry automatically
- Apply bounded retries
- Apply backoff
- Record attempts

### Source Failures

Examples:

- Website structure changed
- Source unavailable
- Authentication expired
- Access method no longer works

Response:

- Mark source degraded
- Stop unsafe repeated attempts
- Preserve failure evidence
- Escalate when required

### Data-Quality Failures

Examples:

- Invalid format
- Missing required fields
- Conflicting information

Response:

- Preserve original record
- Quarantine or flag record
- Prevent bad data from silently entering trusted datasets

### Agent/Service Failures

Response:

- Attempt safe restart/recovery
- Record diagnostic information
- Escalate repeated failures

### Business-Logic Failures

Potentially unsafe workflows should pause rather than continue blindly.

The Supervisor may:

- Detect
- Diagnose
- Retry
- Restart
- Reassign
- Quarantine
- Escalate

The Supervisor shall not have unlimited authority to modify business
data or make consequential commercial decisions.

---

## FR-009 — Evidence, Provenance & Relationship History

Traceability is a core platform requirement.

The platform should preserve enough information to answer:

> Where did this information come from, when was it discovered, what
> happened to it afterward, and what interactions have occurred?

Where applicable, records should retain:

- Original source
- Source URL/reference
- Discovery timestamp
- Original/raw evidence
- Agent/service responsible
- Run ID
- Transformation history
- Verification history
- Enrichment history
- Status changes
- Relationship/contact history
- Follow-up history

Curated data should remain traceable back to its originating evidence.

This provenance model is a core component of platform trust.

---

## FR-010 — Human Authority & Approval Boundaries

The platform shall use three authority zones.

### GREEN — Autonomous

The system may perform these operations without human approval.

Examples:

- Discovery
- Data extraction
- Data cleaning
- Standardization
- Deduplication
- Classification
- Monitoring
- Safe enrichment
- Data-quality checks
- Safe retries
- Operational health checks

### YELLOW — AI-Assisted / Human Approved

AI may analyze, recommend, rank, or draft, but a human approves the
consequential action.

Examples:

- Buyer-supplier match recommendations
- Opportunity prioritization
- Outreach drafts
- Follow-up drafts
- Suggested responses
- Supplier recommendations
- Exception-resolution recommendations

### RED — Human Only

The system must not independently make or execute consequential
commercial, legal, or financial decisions.

Examples:

- Final pricing
- Binding quotations
- Accepting orders
- Contractual commitments
- Payment commitments
- Payment-term acceptance
- Regulatory/compliance representations
- Final supplier commitments
- High-risk external communications

Supervisor capabilities are subject to the same boundaries.

Consequential actions shall be auditable.

---

# 5. Initial Platform Components

The current conceptual platform consists of:

1. Aeropex Control Panel
2. Supervisor / Operations Control
3. Buyer Discovery capability
4. Supplier Discovery capability
5. Source Registry
6. Data Engineering Platform
7. Verification & Research capability
8. Buyer-Supplier Matching capability
9. Outreach capability
10. Human Approval layer

Not every capability must be implemented as an LLM agent.

Deterministic software, SQL, PySpark, APIs, scheduled jobs, rules, and
traditional services should be preferred where AI reasoning is
unnecessary.

---

# 6. Conceptual Data Flow

```text
Approved Sources
      |
      v
Buyer Discovery -------- Supplier Discovery
      |                         |
      +------------+------------+
                   |
                   v
             Raw / Bronze
               ADLS Gen2
                   |
                   v
          Azure Data Factory
                   |
                   v
        Databricks / PySpark
                   |
             Silver Layer
                   |
                   v
              Gold Layer
                   |
        +----------+----------+
        |                     |
        v                     v
Verification/Research      Analytics
        |
        v
Buyer-Supplier Matching
        |
        v
Outreach Preparation
        |
        v
Human Approval
        |
        v
Commercial Action

```
---

# 7. Control & Supervision Model

The Supervisor/Operations layer exists to coordinate and observe
platform workflows.

It should eventually understand:

Which services are healthy
Which jobs are running
Which jobs failed
Which sources are degraded
Which records are quarantined
Which workflows are waiting
Which items require human attention

It may perform bounded recovery operations.

It should expose operational summaries and decisions through the
Control Panel.

The platform should store concise audit summaries of supervisor
actions and decisions.

Internal model reasoning/chain-of-thought is not a platform
requirement.


# 8. Initial Delivery Strategy

The platform shall be built incrementally.

We will not attempt to implement every agent simultaneously.

Initial implementation sequence:

Establish requirements baseline.
Design system architecture.
Define data contracts.
Build Control Panel V0.1.
Build Buyer Discovery V0.1.
Connect discovery output to persistent storage.
Test the vertical workflow.
Introduce monitoring/supervision.
Add data-engineering processing.
Add verification/research.
Add supplier discovery.
Add matching.
Add outreach preparation.
Expand products, countries, and sources.

Each stage must be independently testable.

# 9. Engineering Principles

The project shall follow these principles:

Production-Oriented Design

Design for reliability, observability, maintainability, and
traceability rather than demo-only behavior.

Configuration Over Hard-Coding

Products, sources, schedules, and similar business configuration should
not require application code changes where avoidable.

Evidence First

Preserve original evidence before enrichment or transformation.

Deterministic Before AI

Use conventional software for deterministic operations.

Use advanced AI reasoning only where reasoning materially improves the
result.

Human-in-the-Loop

Maintain human authority over consequential actions.

Small, Testable Components

Avoid large autonomous "mega-agents."

Capabilities should have explicit responsibilities, inputs, outputs,
failure behavior, and authority boundaries.

Observability by Default

Important workflows should generate structured logs, status events,
metrics, and audit records.

Data as Shared Platform Memory

Agents/services should not become isolated stores of business
knowledge.

Persistent platform data is the shared source of operational memory.

# 10. Documentation & Development Process

Development shall follow the following engineering cycle:

Business Problem
      ↓
Requirements
      ↓
Architecture
      ↓
Data Contracts
      ↓
Technical Specification
      ↓
Bounded Implementation
      ↓
Automated Testing
      ↓
Engineering Review
      ↓
Integration
      ↓
Documentation Update
      ↓
Git Commit / Pull Request

AI coding tools such as Codex may accelerate implementation, but
architecture and requirements should be defined before delegating
substantial implementation work.

This document is a living engineering artifact and shall be updated as
the platform evolves.

---

# 11. Current Scope

Current Phase: Requirements Definition

Requirements Baseline: FR-001 through FR-010

Next Phase: System Architecture V0.1

No production implementation should begin until the initial
architecture and core data contracts have been reviewed.

# 12. Open Decisions

The following items remain intentionally unresolved and should be
addressed during architecture/design:

Backend technology stack
Frontend technology stack
Operational database
Event/message architecture
Agent orchestration implementation
LLM/model routing strategy
Authentication implementation
RBAC implementation
Azure deployment topology
Development vs production environments
Observability stack
Source connector architecture
Cost controls
Secrets management
CI/CD strategy
Testing strategy
Detailed canonical data model

These are design decisions, not assumptions.

# 13. Change Log
v0.1 — September 10, 2026

Initial requirements baseline established.

Defined:

Operational Control Panel
Multi-channel ingestion
Entity-specific data quality
Configurable product discovery
HS-code-aware product configuration
Dynamic source discovery and governance
Buyer/contact enrichment
Scheduled/manual/event-driven execution
Failure handling and recovery
Evidence and provenance
Relationship history
Human authority boundaries
Incremental implementation strategy
