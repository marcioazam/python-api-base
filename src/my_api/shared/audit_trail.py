"""Enhanced Audit Trail with diff tracking and snapshots."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Protocol, Any
import json
import hashlib


class AuditAction(Enum):
    """Audit action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    RESTORE = "restore"
    ARCHIVE = "archive"


@dataclass
class FieldChange:
    """Single field change."""
    field_name: str
    old_value: Any
    new_value: Any
    field_type: str = "unknown"


@dataclass
class AuditEntry:
    """Audit log entry with diff tracking."""
    id: str
    entity_type: str
    entity_id: str
    action: AuditAction
    timestamp: datetime
    user_id: str | None
    user_ip: str | None = None
    changes: list[FieldChange] = field(default_factory=list)
    before_snapshot: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        content = f"{self.entity_type}{self.entity_id}{self.action.value}"
        content += json.dumps(self.before_snapshot, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class AuditBackend(Protocol):
    """Protocol for audit storage backend."""

    async def save(self, entry: AuditEntry) -> None: ...
    async def find_by_entity(
        self, entity_type: str, entity_id: str
    ) -> list[AuditEntry]: ...
    async def find_by_user(self, user_id: str) -> list[AuditEntry]: ...
    async def find_by_time_range(
        self, start: datetime, end: datetime
    ) -> list[AuditEntry]: ...


class DiffCalculator:
    """Calculate differences between object states."""

    @staticmethod
    def compute_diff(
        before: dict[str, Any] | None,
        after: dict[str, Any] | None
    ) -> list[FieldChange]:
        """Compute field-level differences."""
        changes: list[FieldChange] = []

        if before is None:
            before = {}
        if after is None:
            after = {}

        all_keys = set(before.keys()) | set(after.keys())

        for key in all_keys:
            old_val = before.get(key)
            new_val = after.get(key)

            if old_val != new_val:
                changes.append(FieldChange(
                    field_name=key,
                    old_value=old_val,
                    new_value=new_val,
                    field_type=type(new_val).__name__ if new_val else "null"
                ))

        return changes

    @staticmethod
    def apply_diff(
        base: dict[str, Any],
        changes: list[FieldChange]
    ) -> dict[str, Any]:
        """Apply changes to reconstruct state."""
        result = dict(base)
        for change in changes:
            if change.new_value is None:
                result.pop(change.field_name, None)
            else:
                result[change.field_name] = change.new_value
        return result


class AuditService[T]:
    """Enhanced audit service with diff tracking."""

    def __init__(self, backend: AuditBackend) -> None:
        self._backend = backend
        self._diff_calc = DiffCalculator()

    def _to_dict(self, obj: T | None) -> dict[str, Any] | None:
        if obj is None:
            return None
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return dict(obj) if isinstance(obj, dict) else {"value": obj}

    async def log_create(
        self,
        entity_type: str,
        entity_id: str,
        entity: T,
        user_id: str | None = None,
        user_ip: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> AuditEntry:
        """Log entity creation."""
        import uuid
        after = self._to_dict(entity)
        changes = self._diff_calc.compute_diff(None, after)

        entry = AuditEntry(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.CREATE,
            timestamp=datetime.now(UTC),
            user_id=user_id,
            user_ip=user_ip,
            changes=changes,
            before_snapshot=None,
            after_snapshot=after,
            metadata=metadata or {}
        )

        await self._backend.save(entry)
        return entry

    async def log_update(
        self,
        entity_type: str,
        entity_id: str,
        before: T,
        after: T,
        user_id: str | None = None,
        user_ip: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> AuditEntry:
        """Log entity update with diff."""
        import uuid
        before_dict = self._to_dict(before)
        after_dict = self._to_dict(after)
        changes = self._diff_calc.compute_diff(before_dict, after_dict)

        entry = AuditEntry(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.UPDATE,
            timestamp=datetime.now(UTC),
            user_id=user_id,
            user_ip=user_ip,
            changes=changes,
            before_snapshot=before_dict,
            after_snapshot=after_dict,
            metadata=metadata or {}
        )

        await self._backend.save(entry)
        return entry

    async def log_delete(
        self,
        entity_type: str,
        entity_id: str,
        entity: T,
        user_id: str | None = None,
        user_ip: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> AuditEntry:
        """Log entity deletion."""
        import uuid
        before = self._to_dict(entity)

        entry = AuditEntry(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.DELETE,
            timestamp=datetime.now(UTC),
            user_id=user_id,
            user_ip=user_ip,
            changes=self._diff_calc.compute_diff(before, None),
            before_snapshot=before,
            after_snapshot=None,
            metadata=metadata or {}
        )

        await self._backend.save(entry)
        return entry

    async def get_history(
        self,
        entity_type: str,
        entity_id: str
    ) -> list[AuditEntry]:
        """Get complete history for an entity."""
        return await self._backend.find_by_entity(entity_type, entity_id)

    async def reconstruct_at(
        self,
        entity_type: str,
        entity_id: str,
        timestamp: datetime
    ) -> dict[str, Any] | None:
        """Reconstruct entity state at a point in time."""
        history = await self.get_history(entity_type, entity_id)
        history = sorted(history, key=lambda e: e.timestamp)

        state: dict[str, Any] | None = None
        for entry in history:
            if entry.timestamp > timestamp:
                break
            if entry.action == AuditAction.CREATE:
                state = entry.after_snapshot
            elif entry.action == AuditAction.UPDATE and state:
                state = self._diff_calc.apply_diff(state, entry.changes)
            elif entry.action == AuditAction.DELETE:
                state = None

        return state


class InMemoryAuditBackend:
    """In-memory audit backend for testing."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    async def save(self, entry: AuditEntry) -> None:
        self._entries.append(entry)

    async def find_by_entity(
        self, entity_type: str, entity_id: str
    ) -> list[AuditEntry]:
        return [
            e for e in self._entries
            if e.entity_type == entity_type and e.entity_id == entity_id
        ]

    async def find_by_user(self, user_id: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.user_id == user_id]

    async def find_by_time_range(
        self, start: datetime, end: datetime
    ) -> list[AuditEntry]:
        return [
            e for e in self._entries
            if start <= e.timestamp <= end
        ]
