"""Celery application configuration.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 8.1**
"""

from celery import Celery

try:
    from my_app.core.config.settings import get_settings
    settings = get_settings()
    broker_url = settings.redis.url
except Exception:
    broker_url = "redis://localhost:6379/0"


def create_celery_app(
    name: str = "my_app",
    broker: str | None = None,
    backend: str | None = None,
) -> Celery:
    """Create and configure Celery application.
    
    Args:
        name: Application name.
        broker: Message broker URL.
        backend: Result backend URL.
        
    Returns:
        Configured Celery application.
    """
    app = Celery(
        name,
        broker=broker or broker_url,
        backend=backend or broker_url,
    )
    
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour
        task_soft_time_limit=3300,  # 55 minutes
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
    )
    
    return app


# Default Celery app instance
celery_app = create_celery_app()
