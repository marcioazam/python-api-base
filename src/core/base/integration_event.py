"""Integration events for cross-context communication.

Integration events are used for communication between bounded contexts
or with external systems, unlike domain events which are internal.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 1.4**
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

try:
    from my_app.shared.utils.time import utc_now
except ImportError:
    from datetime import timezone
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class IntegrationEvent:
    """Base class for integration events.
    
    Integration events are used for:
    - Communication between bounded contexts
    - Publishing to external message brokers (Kafka, RabbitMQ)
    - Triggering workflows in other services
    
    Unlike domain events, integration events:
    - Are serializable for transport over the network
    - Include routing information (source, destination)
    - May be versioned for backward compatibility
    """
    
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=utc_now)
    source_context: str = ""
    correlation_id: str | None = None
    causation_id: str | None = None
    version: int = 1
    
    @property
    def event_type(self) -> str:
        """Return the event type identifier."""
        return f"{self.source_context}.{self.__class__.__name__}"
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary for transport.
        
        Returns:
            Dictionary representation of the event.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "source_context": self.source_context,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "version": self.version,
            "payload": self._get_payload(),
        }
    
    def _get_payload(self) -> dict[str, Any]:
        """Get event-specific payload data.
        
        Override in subclasses to include event-specific data.
        
        Returns:
            Dictionary with event payload.
        """
        return {}


@dataclass(frozen=True, slots=True)
class UserRegisteredIntegrationEvent(IntegrationEvent):
    """Integration event for user registration."""
    
    user_id: str = ""
    email: str = ""
    source_context: str = "users"
    
    def _get_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
        }


@dataclass(frozen=True, slots=True)
class UserDeactivatedIntegrationEvent(IntegrationEvent):
    """Integration event for user deactivation."""
    
    user_id: str = ""
    reason: str = ""
    source_context: str = "users"
    
    def _get_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class OrderCreatedIntegrationEvent(IntegrationEvent):
    """Integration event for order creation."""
    
    order_id: str = ""
    user_id: str = ""
    total_amount: float = 0.0
    source_context: str = "orders"
    
    def _get_payload(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "total_amount": self.total_amount,
        }
