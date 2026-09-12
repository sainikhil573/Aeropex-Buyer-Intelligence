from aeropex_workers.celery_app import health_check_task


def test_health_check_task() -> None:
    assert health_check_task() == {"status": "ok", "service": "aeropex-worker"}
