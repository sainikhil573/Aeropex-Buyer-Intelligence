# Aeropex Buyer Intelligence Data Platform

Aeropex Buyer Intelligence is an internal, production-oriented data and operations platform for discovering, preserving, validating, and eventually acting on buyer intelligence for Aeropex Exports.

Current milestone: **M1.3 Control Panel Operational Dashboard**.

Buyer Discovery, scraping/browser automation, business workflows, and AI/model integrations are **not implemented yet**.

## Architecture Summary

- Frontend: Next.js / React control panel shell.
- Backend: FastAPI with `/api/v1` routing plus `/health` and `/ready`.
- Contracts: Pydantic V0.1 data contracts kept separate from persistence models.
- Operational database: PostgreSQL through SQLAlchemy and Alembic.
- Operational persistence: Agent, AgentRun, ErrorEvent, and AuditEvent.
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

`POST /api/v1/runs` queues only the safe operational test task. It does not start Buyer Discovery.

## Run Migrations

```powershell
alembic upgrade head
```

The M1.2 migration creates the operational tables and registers the initial Buyer Discovery agent:

```text
AGT-BUYER-DISCOVERY-001
```

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

Functional M1.3 pages:

- `/` Overview
- `/agents`
- `/agents/{agentId}`
- `/runs/{runId}`
- `/system-health`

Buyer Intelligence, Suppliers, Sources, Approvals, and Data Pipeline remain clearly labeled future-milestone placeholders.

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
- Buyer, supplier, matching, outreach, and verification persistence
- Azure resource provisioning

## Change Log

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
