"""connection_pool enums."""

from enum import Enum


class ConnectionState(str, Enum):
    """Connection state."""

    IDLE = "idle"
    IN_USE = "in_use"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"
