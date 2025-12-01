"""Security audit logger models.

**Feature: full-codebase-review-2025, Task 1.4: Refactor audit_logger**
**Validates: Requirements 9.2**
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import SecurityEventType


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """Immutable security event record with correlation ID.

    **Feature: core-improvements-v2**
    **Validates: Requirements 4.5**
    """

    event_type: SecurityEventType
    timestamp: datetime
    correlation_id: str
    client_ip: str | None = None
    user_id: str | None = None
    resource: str | None = None
    action: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for logging."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "client_ip": self.client_ip,
            "user_id": self.user_id,
            "resource": self.resource,
            "action": self.action,
            "reason": self.reason,
            **self.metadata,
        }
