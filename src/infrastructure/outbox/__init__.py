"""Outbox pattern implementation for reliable event publishing.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.4**
"""

from my_app.infrastructure.outbox.models import (
    OutboxEntry,
    OutboxStatus,
    OutboxRepository,
    EventPublisher,
    InMemoryOutboxRepository,
    OutboxService,
)
from my_app.infrastructure.outbox.repository import (
    OutboxModel,
    SQLAlchemyOutboxRepository,
)
from my_app.infrastructure.outbox.dispatcher import (
    OutboxDispatcher,
    OutboxDispatcherService,
    DispatcherConfig,
)

__all__ = [
    # Models
    "OutboxEntry",
    "OutboxStatus",
    "OutboxModel",
    # Protocols
    "OutboxRepository",
    "EventPublisher",
    # Implementations
    "InMemoryOutboxRepository",
    "SQLAlchemyOutboxRepository",
    # Services
    "OutboxService",
    "OutboxDispatcher",
    "OutboxDispatcherService",
    "DispatcherConfig",
]
