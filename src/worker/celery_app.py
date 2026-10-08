"""Celery application configuration. Broker: Redis (redis://redis:6379/0 in Docker)."""
from celery import Celery

from src.config import settings

# Redis as broker and result backend (e.g. redis://redis:6379/0 inside Docker)
celery_app = Celery(
    "leadiagent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.worker.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
