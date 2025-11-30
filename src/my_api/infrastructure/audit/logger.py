"""Audit logging service for tracking security-relevant events.

**Feature: api-base-improvements, infrastructure-code-review**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3**
"""

import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

from my_api.shared.utils.ids import generate_ulid

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Standard audit action types."""

    # Authentication actions
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"

    # Authorization actions
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # Data actions
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # System actions
    CONFIG_CHANGE = "config_change"
    EXPORT = "export"
    IMPORT = "import"


class AuditResult(str, Enum):
    """Audit action result types."""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Audit log entry.

    Attributes:
        id: Unique entry identifier (ULID).
        timestamp: When the action occurred.
        user_id: User who performed the action (None for anonymous).
        action: Type of action performed.
        resource_type: Type of resource affected.
        resource_id: ID of the affected resource.
        details: Additional action details.
        ip_address: Client IP address.
        user_agent: Client user agent string.
        result: Action result (success/failure/error).
        request_id: Correlation ID for request tracing.
    """

    id: str
    timestamp: datetime
    action: str
    resource_type: str
    result: str
    user_id: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "result": self.result,
            "request_id": self.request_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEntry":
        """Create entry from dictionary.
        
        Args:
            data: Dictionary containing audit entry data.
            
        Returns:
            AuditEntry instance.
            
        Raises:
            KeyError: If required fields are missing.
            ValueError: If timestamp format is invalid.
        """
        # Validate required fields
        required_fields = ["id", "timestamp", "action", "resource_type", "result"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise KeyError(f"Missing required fields: {', '.join(missing)}")

        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # Ensure timestamp is timezone-aware (assume UTC if naive)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        return cls(
            id=data["id"],
            timestamp=timestamp,
            user_id=data.get("user_id"),
            action=data["action"],
            resource_type=data["resource_type"],
            resource_id=data.get("resource_id"),
            details=data.get("details", {}),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            result=data["result"],
            request_id=data.get("request_id"),
        )

    def to_json(self) -> str:
        """Serialize entry to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "AuditEntry":
        """Deserialize entry from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class AuditFilters:
    """Filters for querying audit logs.

    Attributes:
        user_id: Filter by user ID.
        action: Filter by action type.
        resource_type: Filter by resource type.
        start_date: Filter entries after this date.
        end_date: Filter entries before this date.
        result: Filter by result type.
        limit: Maximum number of entries to return.
        offset: Number of entries to skip.
    """

    user_id: str | None = None
    action: str | None = None
    resource_type: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    result: str | None = None
    limit: int = 100
    offset: int = 0


class AuditLogger(ABC):
    """Abstract base class for audit logging."""

    @abstractmethod
    async def log(self, entry: AuditEntry) -> None:
        """Log an audit entry.

        Args:
            entry: Audit entry to log.
        """
        ...

    @abstractmethod
    async def query(self, filters: AuditFilters) -> list[AuditEntry]:
        """Query audit logs with filters.

        Args:
            filters: Query filters.

        Returns:
            List of matching audit entries.
        """
        ...

    async def log_action(
        self,
        action: str | AuditAction,
        resource_type: str,
        result: str | AuditResult = AuditResult.SUCCESS,
        user_id: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditEntry:
        """Convenience method to create and log an audit entry.

        Args:
            action: Action type.
            resource_type: Type of resource.
            result: Action result.
            user_id: User who performed action.
            resource_id: ID of affected resource.
            details: Additional details.
            ip_address: Client IP.
            user_agent: Client user agent.
            request_id: Request correlation ID.

        Returns:
            The created audit entry.
        """
        action_str = action.value if isinstance(action, AuditAction) else action
        result_str = result.value if isinstance(result, AuditResult) else result

        entry = AuditEntry(
            id=generate_ulid(),
            timestamp=datetime.now(UTC),
            user_id=user_id,
            action=action_str,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            result=result_str,
            request_id=request_id,
        )

        await self.log(entry)
        return entry


class InMemoryAuditLogger(AuditLogger):
    """In-memory audit logger for development and testing."""

    def __init__(self, max_entries: int = 10000) -> None:
        """Initialize in-memory audit logger.

        Args:
            max_entries: Maximum entries to keep in memory.
        """
        self._entries: list[AuditEntry] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()

    async def log(self, entry: AuditEntry) -> None:
        """Log an audit entry to memory."""
        with self._lock:
            self._entries.append(entry)

            # Trim old entries if over limit (keep newest)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

        logger.debug(
            f"Audit: {entry.action} on {entry.resource_type} "
            f"by {entry.user_id or 'anonymous'} - {entry.result}"
        )

    async def query(self, filters: AuditFilters) -> list[AuditEntry]:
        """Query audit logs with filters."""
        with self._lock:
            results = self._entries.copy()

        # Apply filters
        if filters.user_id:
            results = [e for e in results if e.user_id == filters.user_id]

        if filters.action:
            results = [e for e in results if e.action == filters.action]

        if filters.resource_type:
            results = [e for e in results if e.resource_type == filters.resource_type]

        if filters.result:
            results = [e for e in results if e.result == filters.result]

        if filters.start_date:
            results = [e for e in results if e.timestamp >= filters.start_date]

        if filters.end_date:
            results = [e for e in results if e.timestamp <= filters.end_date]

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply pagination
        return results[filters.offset : filters.offset + filters.limit]

    def clear(self) -> None:
        """Clear all entries (for testing)."""
        self._entries.clear()
