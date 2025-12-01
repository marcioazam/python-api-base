"""Celery Beat schedule configuration."""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "cleanup-outbox": {
        "task": "my_app.infrastructure.tasks.workers.cleanup_outbox",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "maintenance"},
    },
    "rebuild-read-models-daily": {
        "task": "my_app.infrastructure.tasks.workers.rebuild_read_models",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "maintenance"},
    },
    "health-check": {
        "task": "my_app.infrastructure.tasks.workers.health_check",
        "schedule": 60.0,
        "options": {"queue": "default"},
    },
}
