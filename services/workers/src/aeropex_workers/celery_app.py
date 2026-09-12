"""Celery application configuration."""

from aeropex_api.core.config import get_settings
from celery import Celery

settings = get_settings()

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
