from celery import Celery

from src.config.settings import settings
from src.workers.schedules import beat_schedule

# Initialize Celery
# TODO add includes
# Example: include=["src.workers.tasks.task1", "src.workers.tasks.task2"]
celery_app = Celery(
    "minirag",
    broker=settings.REDIS_URL,
    backend=f"db+{settings.DATABASE_URL_SYNC}",  # PostgreSQL as result backend
    include=[],
)

# Configuration
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing (separate queues for different priorities)
    # TODO: Define task_routes if needed, e.g., for different task types or priorities
    # Example:"src.workers.tasks.*": {"queue": "..."},
    task_routes={},
    # Reliability settings
    task_acks_late=True,  # Acknowledge after task completes (not before)
    task_reject_on_worker_lost=True,  # Requeue task if worker dies
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
    # Result settings
    result_expires=3600,  # Delete results after 1 hour
    # Retry settings
    task_default_retry_delay=60,  # 1 minute default retry delay
)

# Import schedules (for Celery Beat)
celery_app.conf.beat_schedule = beat_schedule
