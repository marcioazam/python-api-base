"""RBAC audit logging with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R14.5 - Audit logging for access control**
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Audit Event
# =============================================================================


@dataclass(frozen=True, slots=True)
class AuditEvent[TUser, TResource: Enum, TAction: Enum]:
    """Typed audit event for RBAC access.

    **Requirement: R14.5 - Typed AuditEvent[TUser, TResource, TAction]**

    Type Parameters:
        TUser: User type.
        TResource: Resource enum type.
        TAction: Action enum type.
    """

    event_id: str
    timestamp: datetime
    user_id: str
    user_roles: list[str]
    resource: TResource
    action: TAction
    resource_id: str | None
    granted: bool
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create[TU, TR: Enum, TA: Enum](
        cls,
        user_id: str,
        user_roles: list[str],
        resource: TR,
        action: TA,
        resource_id: str | None,
        granted: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "AuditEvent[TU, TR, TA]":
        """Create new audit event.

        Args:
            user_id: User identifier.
            user_roles: User's assigned roles.
            resource: Resource being accessed.
            action: Action being performed.
            resource_id: Optional specific resource ID.
            granted: Whether access was granted.
            ip_address: Client IP address.
            user_agent: Client user agent.
            metadata: Additional metadata.

        Returns:
            New audit event.
        """
        return cls(
            event_id=str(uuid4()),
            timestamp=datetime.now(UTC),
            user_id=user_id,
            user_roles=user_roles,
            resource=resource,
            action=action,
            resource_id=resource_id,
            granted=granted,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_roles": self.user_roles,
            "resource": self.resource.value,
            "action": self.action.value,
            "resource_id": self.resource_id,
            "granted": self.granted,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata,
        }


# =============================================================================
# Audit Logger
# =============================================================================


class AuditLogger[TUser, TResource: Enum, TAction: Enum]:
    """Generic audit logger for RBAC events.

    Type Parameters:
        TUser: User type.
        TResource: Resource enum type.
        TAction: Action enum type.
    """

    def __init__(
        self,
        logger_name: str = "rbac.audit",
        sink: Any | None = None,
    ) -> None:
        """Initialize audit logger.

        Args:
            logger_name: Python logger name.
            sink: Optional external sink (e.g., Elasticsearch, database).
        """
        self._logger = logging.getLogger(logger_name)
        self._sink = sink
        self._handlers: list[Any] = []

    async def log(
        self,
        event: AuditEvent[TUser, TResource, TAction],
    ) -> None:
        """Log audit event.

        Args:
            event: Audit event to log.
        """
        event_dict = event.to_dict()

        # Log to Python logger
        if event.granted:
            self._logger.info(
                "Access granted",
                extra={"audit_event": event_dict},
            )
        else:
            self._logger.warning(
                "Access denied",
                extra={"audit_event": event_dict},
            )

        # Send to external sink if configured
        if self._sink:
            try:
                await self._sink.write(event_dict)
            except Exception as e:
                self._logger.error(f"Failed to write to audit sink: {e}")

        # Call registered handlers
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                self._logger.error(f"Audit handler failed: {e}")

    async def log_access(
        self,
        user_id: str,
        user_roles: list[str],
        resource: TResource,
        action: TAction,
        resource_id: str | None,
        granted: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Convenience method to log access.

        Args:
            user_id: User identifier.
            user_roles: User's roles.
            resource: Resource type.
            action: Action type.
            resource_id: Optional resource ID.
            granted: Whether access was granted.
            ip_address: Client IP.
            user_agent: Client user agent.
            metadata: Additional metadata.
        """
        event = AuditEvent.create(
            user_id=user_id,
            user_roles=user_roles,
            resource=resource,
            action=action,
            resource_id=resource_id,
            granted=granted,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
        await self.log(event)

    def add_handler(
        self,
        handler: Any,
    ) -> None:
        """Add async handler for audit events.

        Args:
            handler: Async callable to receive events.
        """
        self._handlers.append(handler)

    def remove_handler(self, handler: Any) -> None:
        """Remove handler.

        Args:
            handler: Handler to remove.
        """
        self._handlers.remove(handler)


# =============================================================================
# Audit Sink Protocol
# =============================================================================


class AuditSink(Protocol):
    """Protocol for audit event sinks."""

    async def write(self, event: dict[str, Any]) -> None:
        """Write audit event.

        Args:
            event: Event dictionary.
        """
        ...


class InMemoryAuditSink:
    """In-memory audit sink for testing."""

    def __init__(self) -> None:
        """Initialize sink."""
        self._events: list[dict[str, Any]] = []

    async def write(self, event: dict[str, Any]) -> None:
        """Write event to memory."""
        self._events.append(event)

    @property
    def events(self) -> list[dict[str, Any]]:
        """Get all events."""
        return self._events

    def clear(self) -> None:
        """Clear all events."""
        self._events.clear()
