# Aeropex Buyer Intelligence Data Platform

Aeropex Buyer Intelligence is an internal, production-oriented data and operations platform for discovering, preserving, validating, and eventually acting on buyer intelligence for Aeropex Exports.

Current milestone: **M1.1 Platform Foundation**.

Buyer Discovery, scraping/browser automation, business workflows, and AI/model integrations are **not implemented yet**.

## Architecture Summary

- Frontend: Next.js / React control panel shell.
- Backend: FastAPI with `/api/v1` routing plus `/health` and `/ready`.
- Contracts: Pydantic V0.1 data contracts kept separate from persistence models.
- Operational database foundation: PostgreSQL through SQLAlchemy with Alembic prepared.
- Async execution foundation: Redis and Celery with a safe `health_check_task`.
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

## Run Celery

```powershell
celery -A aeropex_workers.celery_app.celery_app worker --loglevel=INFO
```

The only M1.1 task is `aeropex.health_check_task`.

## Run Tests

```powershell
pytest
```

Unit and contract tests do not require PostgreSQL or Redis.

## Start the Next.js Frontend

```powershell
cd apps/web
npm install
npm run dev
```

The initial control panel shell includes placeholders for Overview, Agents, Buyer Intelligence, Suppliers, Sources, Approvals, Data Pipeline, and System Health.

## Deferred

- Buyer Discovery
- Supplier Discovery
- Scraping/browser automation
- LLM/model integrations
- Human approval workflows
- Production database schema beyond migration-ready foundations
- Azure resource provisioning
