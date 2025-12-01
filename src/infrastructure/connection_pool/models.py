"""connection_pool models."""

from dataclasses import dataclass, field
from datetime import datetime, UTC

from .enums import ConnectionState


@dataclass
class ConnectionInfo:
    """Information about a pooled connection.

    Attributes:
        id: Unique connection identifier.
        state: Current connection state.
        created_at: Connection creation time.
        last_used_at: Last time connection was used.
        use_count: Number of times connection was used.
        health_check_failures: Consecutive health check failures.
    """

    id: str
    state: ConnectionState = ConnectionState.IDLE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    use_count: int = 0
    health_check_failures: int = 0
