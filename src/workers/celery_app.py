from celery import Celery

from src.config.settings import settings
from src.workers.schedules import beat_schedule

# 1. تحديث الـ include لضمان قراءة سيلري للمهام
# بما أنك تستخدم __init__.py يمكنك كتابة مسار المجلد،
# أو كتابة مسار الملفات بشكل صريح لضمان التحميل
celery_app = Celery(
    "minirag",
    broker=settings.REDIS_URL,
    backend=f"db+{settings.DATABASE_URL_SYNC}",
    include=[
        "src.workers.tasks.file_processing",  # أو اسم الملف الفعلي عندك إذا كان file_processing_2
        "src.workers.tasks.index_data",
    ],
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # 2. تحديد الطوابير (Queues) المخصصة لكل مهمة
    task_routes={
        # توجيه مهمة التقطيع إلى طابور اسمه 'processing'
        "tasks.process_assets": {"queue": "processing"},
        # توجيه مهمة الفهرسة إلى طابور اسمه 'indexing'
        "tasks.index_assets": {"queue": "indexing"},
    },
    # Reliability settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_default_retry_delay=60,
)

# Import schedules
celery_app.conf.beat_schedule = beat_schedule
