"""Celery application configuration."""

from __future__ import annotations

import logging

from aeropex_api.core.config import get_settings
from aeropex_api.db.session import create_session_factory
from aeropex_api.services.run_lifecycle import AgentRunService
from celery import Celery

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "aeropex_workers",
    broker=settings.resolved_celery_broker_url,
    backend=settings.resolved_celery_result_backend,
)
celery_app.conf.update(
    task_default_queue="aeropex",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="aeropex.health_check_task")
def health_check_task() -> dict[str, str]:
    return {"status": "ok", "service": "aeropex-worker"}


@celery_app.task(name="aeropex.operational_test_run_task", bind=True)
def operational_test_run_task(self, run_id: str, simulate_failure: bool = False) -> dict[str, str]:
    session_factory = create_session_factory()
    with session_factory() as session:
        service = AgentRunService(session)
        run = service.mark_running(run_id)
        logger.info(
            "Operational run started",
            extra={"run_id": run.run_id, "agent_id": run.agent_id, "task_id": self.request.id},
        )
        try:
            if simulate_failure:
                raise RuntimeError("Simulated operational task failure")
            run = service.mark_completed(
                run_id,
                records_processed=1,
                records_created=0,
                summary="Safe operational test run completed.",
            )
            logger.info(
                "Operational run completed",
                extra={
                    "run_id": run.run_id,
                    "agent_id": run.agent_id,
                    "task_id": self.request.id,
                    "status": run.status.value,
                },
            )
            return {"status": run.status.value, "run_id": run.run_id}
        except Exception as exc:
            failed_run = service.mark_failed(
                run_id,
                error_type=exc.__class__.__name__,
                message=str(exc),
                retryable=False,
            )
            logger.exception(
                "Operational run failed",
                extra={
                    "run_id": failed_run.run_id,
                    "agent_id": failed_run.agent_id,
                    "task_id": self.request.id,
                    "status": failed_run.status.value,
                },
            )
            raise
