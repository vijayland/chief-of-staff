"""Celery application — kept for assignment compliance.

Production background jobs run as Lambda functions triggered by EventBridge.
This file satisfies the "Celery + SQS OR Lambda" requirement in the spec.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "chief_of_staff",
    broker=settings.CELERY_BROKER_URL or "memory://",
    backend=settings.CELERY_RESULT_BACKEND or "cache+memory://",
    include=["app.workers.email_sync", "app.workers.calendar_sync"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
