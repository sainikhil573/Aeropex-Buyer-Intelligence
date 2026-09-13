# Aeropex Buyer Intelligence Data Platform

Aeropex Buyer Intelligence is an internal, production-oriented data and operations platform for discovering, preserving, validating, and eventually acting on buyer intelligence for Aeropex Exports.

Current milestone: **M2.6 Buyer Verification + Contact Enrichment**.

Bounded deterministic extraction, SourceObservation evidence persistence, human review workflow, conservative canonical buyer creation/matching, and evidence-backed buyer verification/contact enrichment persistence are implemented. Supplier matching, scraping/browser automation, outreach/business workflows, production research agents, and AI/model integrations are **not implemented yet**.

## Architecture Summary

- Frontend: Next.js / React control panel shell.
- Backend: FastAPI with `/api/v1` routing plus `/health` and `/ready`.
- Contracts: Pydantic V0.1 data contracts kept separate from persistence models.
- Operational database: PostgreSQL through SQLAlchemy and Alembic.
- Operational persistence: Agent, AgentRun, ErrorEvent, and AuditEvent.
- Configuration persistence: Product and Source Registry control-plane entities.
- Connectors: governed connector abstraction and controlled HTTP connector for approved active sources.
- Extraction: bounded deterministic extractor layer that creates immutable SourceObservation evidence from successful ConnectorResult payloads.
- Observation Review: mutable review workflow metadata for SourceObservation records without changing evidence.
- Canonical Buyer Layer: accepted observations can be conservatively resolved into `Buyer` and optional `BuyerRequirement` records, with linkage metadata attached to the observation.
- Buyer Verification: `VerificationResult`, append-only `VerificationEvidence`, `Contact`, and `EnrichmentResult` records support deterministic fixture validation and human review without external research.
- Run lifecycle: queued, running, completed, completed_with_warnings, failed, and cancelled.
- Async execution foundation: Redis and Celery with safe operational test tasks.
- Control Panel: operational overview, agent inspection, run inspection, error visibility, and system health.
- Data engineering direction: Azure Data Factory, ADLS Gen2, Databricks, PySpark, and Delta Lake are documented for future milestones.

## Repository Structure

```text
apps/
  api/
  web/
services/
  agents/
  workers/
packages/
  contracts/
infrastructure/
  docker/
  azure/
tests/
  unit/
  integration/
  contract/
docs/
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop or compatible Docker runtime

## Environment Setup

Copy `.env.example` to `.env` for local development and adjust only local-safe values.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Never commit real credentials or secrets.

## Start PostgreSQL and Redis

```powershell
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

## Run FastAPI

```powershell
uvicorn aeropex_api.main:app --reload --app-dir apps/api/src
```

Health endpoints:

- `GET /health`
- `GET /ready`
- `GET /api/v1/health`

Operational endpoints:

- `GET /api/v1/overview`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`
- `GET /api/v1/runs?limit=50&offset=0&agent_id=AGT-BUYER-DISCOVERY-001`
- `GET /api/v1/runs/{run_id}`
- `POST /api/v1/runs`
- `GET /api/v1/errors?limit=50&offset=0`
- `GET /api/v1/products?limit=50&offset=0&active=true&category=Spices`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/products`
- `PATCH /api/v1/products/{product_id}`
- `GET /api/v1/sources?limit=50&offset=0`
- `GET /api/v1/sources/eligible`
- `GET /api/v1/sources/{source_id}`
- `POST /api/v1/sources`
- `PATCH /api/v1/sources/{source_id}`
- `POST /api/v1/sources/{source_id}/approve`
- `POST /api/v1/sources/{source_id}/reject`
- `POST /api/v1/connectors/test`
- `POST /api/v1/extractions/test`
- `GET /api/v1/observations?limit=50&offset=0`
- `GET /api/v1/observations/{observation_id}`
- `GET /api/v1/observations/{observation_id}/review`
- `PATCH /api/v1/observations/{observation_id}/review`
- `POST /api/v1/observations/{observation_id}/canonicalize`
- `GET /api/v1/buyers?limit=50&offset=0`
- `GET /api/v1/buyers/{buyer_id}`
- `GET /api/v1/buyers/{buyer_id}/requirements`
- `GET /api/v1/buyers/{buyer_id}/verification`
- `POST /api/v1/buyers/{buyer_id}/verification/test`
- `PATCH /api/v1/buyers/{buyer_id}/verification/{verification_id}`
- `GET /api/v1/buyers/{buyer_id}/verification/evidence`
- `GET /api/v1/buyers/{buyer_id}/contacts`
- `GET /api/v1/buyers/{buyer_id}/enrichments`
- `GET /api/v1/requirements/{requirement_id}`

`POST /api/v1/runs` queues only the safe operational test task. It does not start Buyer Discovery.

`POST /api/v1/connectors/test` is a bounded operational test endpoint. It accepts `source_id` and `target_url`, enforces Source Registry eligibility and URL governance, then executes only the configured connector. It is not a general URL fetch endpoint and must not be used as a proxy.

`POST /api/v1/extractions/test` is a bounded controlled-fixture endpoint. It accepts a configured `source_id`, optional `run_id`, optional `target_url`, `content_type`, and controlled `raw_content`; it does not fetch external data. It exists to validate ConnectorResult -> Extractor -> SourceObservation wiring without public internet, crawling, or AI.

## Run Migrations

```powershell
alembic upgrade head
```

The M1.2 migration creates the operational tables and registers the initial Buyer Discovery agent:

```text
AGT-BUYER-DISCOVERY-001
```

The M2.1 migration adds Product and Source Registry tables and seeds idempotent configuration examples. Seeded products intentionally do not fabricate HS codes.

The M2.3 migration adds append-only `source_observations` evidence persistence for extracted candidate observations.

The M2.4 migration adds one active `observation_reviews` workflow row per observation.

The M2.5 migration adds canonical `buyers` and `buyer_requirements` tables with conservative indexes for deterministic entity resolution.

The M2.6 migration adds `verification_results`, `verification_evidence`, `contacts`, and `enrichment_results` for evidence-backed verification and contact enrichment review.

To verify downgrade and upgrade locally:

```powershell
alembic downgrade base
alembic upgrade head
```

## Run Celery

```powershell
celery -A aeropex_workers.celery_app.celery_app worker --loglevel=INFO
```

M1.2 tasks:

- `aeropex.health_check_task`
- `aeropex.operational_test_run_task`

## Run Tests

```powershell
pytest
```

Unit and contract tests do not require PostgreSQL, Redis, Azure, external websites, or LLM APIs.

## Connector Governance

M2.2 introduces the governed source-access layer that future Buyer Discovery workflows will consume.

Connectors acquire source data only. Extractors interpret successful connector results in a separate bounded layer. The HTTP connector does not decide whether content represents a buyer opportunity, does not call AI models, and does not write Buyer, BuyerRequirement, SourceObservation, ADLS, or Bronze records.

Connector execution is allowed only when:

```text
approval_status == approved
AND
operational_status == active
```

Target URLs must be absolute `http` or `https` URLs and their hostname must match the Source Registry domain or a subdomain of that domain. Obvious internal/private destinations such as localhost, loopback, RFC1918 private IPs, link-local addresses, and metadata-service style IPs are rejected by default.

Supported connector types:

- `http`: implemented with explicit timeout, bounded retries, redirect limit, body-size limit, transparent User-Agent, status capture, and content-type capture.
- `api`, `browser`, `manual`: intentionally unsupported by the factory until separate implementations are designed.

Connector settings:

- `CONNECTOR_HTTP_TIMEOUT_SECONDS`
- `CONNECTOR_HTTP_MAX_ATTEMPTS`
- `CONNECTOR_HTTP_MAX_RESPONSE_BYTES`
- `CONNECTOR_HTTP_MAX_REDIRECTS`
- `CONNECTOR_USER_AGENT`
- `CONNECTOR_ALLOW_PRIVATE_NETWORKS`

## Evidence-First Extraction

M2.3 introduces the first interpretation step after source acquisition:

```text
ConnectorResult -> Extractor -> ExtractionResult -> SourceObservation
```

The extraction layer is bounded and deterministic. It currently supports controlled JSON records through `StructuredJsonExtractor`; unsupported content is preserved as unstructured evidence instead of crashing the platform. Missing fields remain null, and extraction does not create `Buyer` or `BuyerRequirement` entities.

Product matching uses exact case-insensitive comparison against active Product names, aliases, and variants. Ambiguous or missing product matches leave `product_id` null while preserving the raw product text in observation metadata.

`SourceObservation` records are operational evidence/provenance records. They are append-only from the API perspective: create via extraction, read by ID, and list with bounded pagination/filtering. There are no update or delete observation endpoints.

## Observation Review Workflow

M2.4 adds a human review workflow over SourceObservation evidence:

```text
SourceObservation -> Buyer Intelligence Inbox -> Open Observation -> Review Evidence -> Save Review
```

Review statuses are `unreviewed`, `needs_review`, `accepted`, and `rejected`. Review state is stored separately in `ObservationReview`; it is mutable workflow metadata, while SourceObservation evidence remains unchanged. `accepted` is not verified, and `rejected` is not deleted.

Each review mutation records an `AuditEvent` with before and after review state. The local V0.1 actor placeholder is `local-admin` until full authentication/RBAC exists.

## Canonical Buyer Entity Resolution

M2.5 introduces the first canonical business-entity layer:

```text
Accepted SourceObservation -> Entity Resolution -> Buyer -> BuyerRequirement -> Observation Linkage -> AuditEvent
```

`SourceObservation` remains immutable evidence. M2.5 only allows controlled updates to `buyer_id` and `requirement_id` linkage metadata after canonicalization. It never modifies `raw_text`, `source_url`, `captured_at`, `evidence_type`, or extracted fields.

`ObservationReview` is human workflow state. `Buyer` is the canonical company entity. `BuyerRequirement` is the canonical purchasing requirement. `accepted` means eligible for canonicalization; it does not mean the company is verified. New buyers always default to `verification_status = unverified`.

Entity resolution V0.1 is deterministic and conservative. It auto-matches only exact normalized company name plus exact normalized country, or exact normalized primary domain when present. Multiple matches return `ambiguous` and leave the observation unlinked. Weak/fuzzy signals do not auto-merge.

## Buyer Verification and Contact Enrichment

M2.6 adds the first verification layer:

```text
Buyer -> VerificationResult -> VerificationEvidence -> Contact / EnrichmentResult -> Human Review -> Buyer status
```

Verification is separate from discovery, extraction, canonicalization, matching, and outreach. `VerificationEvidence` is append-only and never overwrites `SourceObservation`. `EnrichmentResult` preserves provenance and is not automatically promoted into canonical Buyer or Contact fields.

The controlled fixture endpoint creates a pending `VerificationResult`, evidence rows, discovered enrichment rows, and contact candidates only from explicit request values. It does not browse, scrape, call AI, infer emails, infer websites from email domains, or mark buyers verified automatically.

Human review updates the selected `VerificationResult.status` and synchronizes `Buyer.verification_status`. `verified` means identity evidence was reviewed for V0.1; it does not mean financially safe, creditworthy, contractually approved, scam-proof, regulator-approved, or approved for outreach.

## Start the Next.js Frontend

Configure the frontend API base URL. For local development, create `apps/web/.env.local`:

```powershell
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

```powershell
cd apps/web
npm install
npm run dev
```

Open the Control Panel at:

```text
http://localhost:3000
```

Functional M2.1 pages:

- `/` Overview
- `/agents`
- `/agents/{agentId}`
- `/products`
- `/sources`
- `/runs/{runId}`
- `/system-health`
- `/buyer-intelligence`
- `/buyer-intelligence/{observationId}`
- `/buyers`
- `/buyers/{buyerId}`

Suppliers, Approvals, and Data Pipeline remain clearly labeled future-milestone placeholders.

## Execute the Safe Operational Test Run

1. Start PostgreSQL and Redis.
2. Run migrations with `alembic upgrade head`.
3. Start FastAPI.
4. Start Celery.
5. Start Next.js.
6. Open `http://localhost:3000`.
7. Click `Run Operational Test`.

The button calls `POST /api/v1/runs`, queues the existing safe operational test task, and the dashboard refreshes/polls to show the real run lifecycle. It does not perform Buyer Discovery.

## Frontend Validation

```powershell
cd apps/web
npm run lint
npm run test
npm run build
```

## Deferred

- Buyer Discovery
- Supplier Discovery
- Scraping/browser automation
- LLM/model integrations
- Human approval workflows
- Supplier, matching, outreach, production research agents, and external verification connectors
- Azure resource provisioning

## Configuration Governance

Products and sources are platform-owned configuration. Buyer Discovery will consume approved configuration in a future milestone, but M2.1 does not allow discovery runs to create production product/source configuration.

New sources start as `candidate`. A human-controlled action may approve or reject a candidate. Future Buyer Discovery eligibility is defined as:

```text
approval_status == approved
AND
operational_status == active
```

## Change Log

### M2.6 - Buyer Verification + Contact Enrichment

- Added `VerificationResult`, append-only `VerificationEvidence`, `Contact`, and `EnrichmentResult` persistence.
- Added `BuyerVerificationService` with transactional controlled fixture creation, contact dedupe within a buyer, provenance-preserving enrichment, audit events, and human review status sync to `Buyer.verification_status`.
- Added verification, evidence, contacts, and enrichments API endpoints under `/api/v1/buyers/{buyer_id}`.
- Added `/buyers` and `/buyers/{buyerId}` Control Panel pages.
- Added ADR-020 and focused backend/contract/frontend tests.
- Deferred public web research, scraping, browser automation, LLM/Astra, matching, outreach, RFQ, ADLS/ADF/Databricks, and production research agents.

### M2.4 - Buyer Intelligence UI + Observation Review Workflow

- Added `ObservationReviewStatus`, `ObservationReview`, and `UpdateObservationReviewRequest` contracts.
- Added Alembic migration `20260912_0004_m2_4_observation_reviews`.
- Added `ObservationReviewService` for current/default review state, review updates, notes, audit events, and review counts.
- Added review API endpoints and review metadata on observation list/detail responses.
- Added review-status filtering for observation lists without N+1 review lookups.
- Implemented `/buyer-intelligence` as an operations inbox and `/buyer-intelligence/{observationId}` as a review detail page with read-only raw evidence.
- Added Overview review metrics.
- Deferred canonical Buyer/BuyerRequirement creation, verification, entity resolution, enrichment, matching, outreach, AI/Astra, and new connectors.

### M2.3 - Extraction + SourceObservation + Evidence Capture

- Added `ExtractionRequest`, `ExtractionResult`, `ProductContext`, `ExtractionStatus`, and `EvidenceType` shared contracts.
- Added typed extractor interface, `ExtractorFactory`, and deterministic `StructuredJsonExtractor`.
- Added `ExtractionService` to accept successful ConnectorResult payloads, perform deterministic extraction, create immutable SourceObservation rows, and reuse ErrorEvent for failed extraction results.
- Added Alembic migration `20260912_0003_m2_3_source_observations`.
- Added read/list observation endpoints and bounded controlled endpoint `POST /api/v1/extractions/test`.
- Added deterministic product matching against active product names, aliases, and variants only.
- Added unit and contract tests for null preservation, no fabricated values, product matching, unsupported/malformed payloads, observation persistence, API listing/reading, and failed connector skip behavior.
- Deferred verification, entity resolution, Buyer/BuyerRequirement creation, enrichment, matching, outreach, generic HTML scraping, browser automation, and AI extraction.

### M2.2 - Connector Abstraction + Controlled HTTP Connector

- Added `ConnectorRequest`, `ConnectorResult`, and `ConnectorStatus` shared contracts.
- Added a typed connector interface, strict `ConnectorFactory`, and controlled `HttpConnector`.
- Added `ConnectorExecutionService` to load sources, enforce approved+active eligibility, validate governed domains, reject unsafe URL schemes and private/internal targets, execute connectors, and create final ErrorEvents.
- Added bounded operational endpoint `POST /api/v1/connectors/test`.
- Added configurable HTTP timeout, max attempts, response-size limit, redirect limit, User-Agent, and private-network test bypass defaulting to disabled.
- Added deterministic unit/security/contract tests using mocked HTTP transport; no public internet dependency.
- Deferred buyer extraction, AI interpretation, crawling, browser automation, ADLS/Bronze persistence, and discovery scheduling.

### M2.1 - Product Configuration + Source Registry

- Added Product and Source SQLAlchemy persistence, repositories, services, API endpoints, and Alembic migration `20260912_0002_m2_1_product_source_configuration`.
- Added shared Pydantic create/update/read contracts and constrained source access methods.
- Added explicit source approve/reject lifecycle methods and eligible-source filtering.
- Added audit generation for meaningful configuration lifecycle changes.
- Added Products and Source Registry Control Panel pages using the centralized API client.
- Added idempotent bootstrap helpers and focused unit/API/contract tests.
- Deferred Buyer Discovery execution, connectors, scraping, browser automation, AI calls, matching, verification, outreach, ADLS, ADF, and Databricks.

### M1.3 - Control Panel Operational Dashboard

- Added a professional Next.js operations console shell with required navigation.
- Implemented Overview, Agents, Agent Detail, Run Detail, and System Health pages.
- Added a centralized frontend API client using `NEXT_PUBLIC_API_BASE_URL`.
- Added status badges, loading states, empty states, API unavailable states, and manual/light polling refresh.
- Added the `Run Operational Test` control for the existing safe operational Celery task.
- Added bounded operational error visibility through `GET /api/v1/errors`.
- Added a small operational summary endpoint through `GET /api/v1/overview`.
- Added optional agent filtering to `GET /api/v1/runs`.
- Added configurable local CORS support through `CORS_ALLOWED_ORIGINS`.
- Added focused frontend tests for API client behavior and status rendering helpers.
- Deferred Buyer Discovery, scraping, source crawling, auth/RBAC, WebSockets, and business-domain modules.

### M1.2 - Operational Persistence & Run Lifecycle

- Added PostgreSQL-backed operational entities: Agent, AgentRun, ErrorEvent, and AuditEvent.
- Added Alembic migration for operational tables, constraints, indexes, and the initial Buyer Discovery agent registration.
- Added bounded AgentRun lifecycle service with safe transition rules and audit events.
- Added Celery execution tracking for a safe operational test run.
- Added operational API endpoints under `/api/v1`.
- Improved readiness checks for configured PostgreSQL and Redis dependencies.
- Deferred actual Buyer Discovery, scraping, source crawling, LLM calls, RBAC, and business-domain persistence.
