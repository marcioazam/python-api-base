"""RabbitMQ configuration.

**Feature: enterprise-generics-2025**
**Requirement: R3.1 - Task queue configuration**
**Refactored: 2025 - Extracted from rabbitmq.py for SRP compliance**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class RabbitMQConfig:
    """RabbitMQ connection configuration.

    **Requirement: R3.1 - Task queue configuration**
    """

    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    queue_name: str = "tasks"
    exchange: str = ""
    routing_key: str = "tasks"
    prefetch_count: int = 10
    connection_timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))

    @property
    def url(self) -> str:
        """Get AMQP connection URL."""
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.virtual_host}"
