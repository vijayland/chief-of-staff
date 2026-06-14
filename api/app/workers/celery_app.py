from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "agentic",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.email_sync",
        "app.workers.calendar_sync",
        "app.workers.memory_consolidation",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.email_sync.*": {"queue": "email_sync"},
        "app.workers.memory_consolidation.*": {"queue": "memory"},
        "app.workers.calendar_sync.*": {"queue": "default"},
    },
)

celery_app.conf.beat_schedule = {
    "sync-emails-every-5-minutes": {
        "task": "app.workers.email_sync.sync_all_users_email",
        "schedule": crontab(minute=f"*/{settings.EMAIL_SYNC_INTERVAL_MINUTES}"),
    },
    "sync-calendars-every-15-minutes": {
        "task": "app.workers.calendar_sync.sync_all_users_calendar",
        "schedule": crontab(minute="*/15"),
    },
    "consolidate-memory-nightly": {
        "task": "app.workers.memory_consolidation.consolidate_all_users",
        "schedule": crontab(hour=str(settings.MEMORY_CONSOLIDATION_HOUR), minute="0"),
    },
}
