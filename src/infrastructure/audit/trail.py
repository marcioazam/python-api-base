"""Generic audit trail core models with PEP 695 type parameters.

Core audit functionality including records, actions, and change tracking.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 22.1**
**Refactored: 2025 - Split into modular components for maintainability**
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from core.shared.utils.ids import generate_ulid


class AuditAction(Enum):
    """Standard audit actions."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    RESTORE = "RESTORE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ACCESS_DENIED = "ACCESS_DENIED"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"


@dataclass(frozen=True, slots=True)
class AuditRecord[T]:
    """Generic audit record with before/after snapshots.

    Type Parameters:
        T: The type of entity being audited.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.1**
    """

    id: str = field(default_factory=generate_ulid)
    entity_type: str = ""
    entity_id: str = ""
    action: AuditAction = AuditAction.READ
    user_id: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    before: T | None = None
    after: T | None = None
    changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None

    def get_changed_fields(self) -> list[str]:
        """Get list of changed field names."""
        return list(self.changes.keys())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action.value,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "before": self._serialize_snapshot(self.before),
            "after": self._serialize_snapshot(self.after),
            "changes": {k: {"old": v[0], "new": v[1]} for k, v in self.changes.items()},
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    def _serialize_snapshot(self, snapshot: T | None) -> dict | None:
        """Serialize snapshot to dict."""
        if snapshot is None:
            return None
        if isinstance(snapshot, BaseModel):
            return snapshot.model_dump()
        if hasattr(snapshot, "__dict__"):
            return snapshot.__dict__
        return {"value": snapshot}


def compute_changes[T: BaseModel](
    before: T | None, after: T | None
) -> dict[str, tuple[Any, Any]]:
    """Compute changes between two entity states.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.1**

    Args:
        before: Previous entity state.
        after: New entity state.

    Returns:
        Dictionary of field -> (old_value, new_value).
    """
    changes: dict[str, tuple[Any, Any]] = {}

    if before is None and after is None:
        return changes

    if before is None:
        # Creation - all fields are new
        after_dict = after.model_dump() if isinstance(after, BaseModel) else {}
        for key, value in after_dict.items():
            changes[key] = (None, value)
        return changes

    if after is None:
        # Deletion - all fields removed
        before_dict = before.model_dump() if isinstance(before, BaseModel) else {}
        for key, value in before_dict.items():
            changes[key] = (value, None)
        return changes

    # Update - compare fields
    before_dict = before.model_dump() if isinstance(before, BaseModel) else {}
    after_dict = after.model_dump() if isinstance(after, BaseModel) else {}

    all_keys = set(before_dict.keys()) | set(after_dict.keys())
    for key in all_keys:
        old_val = before_dict.get(key)
        new_val = after_dict.get(key)
        if old_val != new_val:
            changes[key] = (old_val, new_val)

    return changes
