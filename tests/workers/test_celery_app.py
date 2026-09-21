from src.config.settings import settings
from src.workers.celery_app import celery_app
from src.workers.schedules import beat_schedule


def test_celery_app_name():
    assert celery_app.main == "minirag"


def test_celery_broker_url():
    assert celery_app.conf.broker_url == settings.REDIS_URL


def test_celery_result_backend():
    assert celery_app.conf.result_backend == f"db+{settings.DATABASE_URL_SYNC}"


def test_celery_serialization_settings():
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.result_serializer == "json"


def test_celery_timezone_settings():
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True


def test_celery_reliability_settings():
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_celery_result_and_retry_settings():
    assert celery_app.conf.result_expires == 3600
    assert celery_app.conf.task_default_retry_delay == 60


def test_celery_task_routes_default():
    assert celery_app.conf.task_routes == {}


def test_celery_beat_schedule_is_loaded():
    assert celery_app.conf.beat_schedule == beat_schedule
