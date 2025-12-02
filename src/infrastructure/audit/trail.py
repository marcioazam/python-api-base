"""Generic audit trail support with PEP 695 type parameters.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 22.1, 22.2, 22.3, 22.4, 22.5**
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

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


@runtime_checkable
class AuditStore[TProvider](Protocol):
    """Generic audit store protocol for multiple backends.

    Type Parameters:
        TProvider: Provider-specific configuration type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.2**
    """

    async def save(self, record: AuditRecord[Any]) -> str:
        """Save audit record.

        Args:
            record: Audit record to save.

        Returns:
            ID of saved record.
        """
        ...

    async def get_by_id(self, record_id: str) -> AuditRecord[Any] | None:
        """Get audit record by ID."""
        ...

    async def get_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        *,
        limit: int = 100,
    ) -> Sequence[AuditRecord[Any]]:
        """Get audit records for an entity."""
        ...

    async def get_by_user(
        self,
        user_id: str,
        *,
        limit: int = 100,
    ) -> Sequence[AuditRecord[Any]]:
        """Get audit records by user."""
        ...

    async def get_by_correlation(
        self,
        correlation_id: str,
    ) -> Sequence[AuditRecord[Any]]:
        """Get audit records by correlation ID."""
        ...


class InMemoryAuditStore:
    """In-memory audit store implementation.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.2**
    """

    def __init__(self) -> None:
        self._records: dict[str, AuditRecord[Any]] = {}

    async def save(self, record: AuditRecord[Any]) -> str:
        """Save audit record."""
        self._records[record.id] = record
        return record.id

    async def get_by_id(self, record_id: str) -> AuditRecord[Any] | None:
        """Get audit record by ID."""
        return self._records.get(record_id)

    async def get_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        *,
        limit: int = 100,
    ) -> Sequence[AuditRecord[Any]]:
        """Get audit records for an entity."""
        records = [
            r
            for r in self._records.values()
            if r.entity_type == entity_type and r.entity_id == entity_id
        ]
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    async def get_by_user(
        self,
        user_id: str,
        *,
        limit: int = 100,
    ) -> Sequence[AuditRecord[Any]]:
        """Get audit records by user."""
        records = [r for r in self._records.values() if r.user_id == user_id]
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    async def get_by_correlation(
        self,
        correlation_id: str,
    ) -> Sequence[AuditRecord[Any]]:
        """Get audit records by correlation ID."""
        return [r for r in self._records.values() if r.correlation_id == correlation_id]


@dataclass
class AuditQueryFilters:
    """Filters for audit queries."""

    entity_type: str | None = None
    entity_id: str | None = None
    user_id: str | None = None
    action: AuditAction | None = None
    correlation_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class AuditQuery[T]:
    """Generic audit query with typed filters.

    Type Parameters:
        T: The entity type being queried.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.3**
    """

    def __init__(self, store: AuditStore[Any]) -> None:
        self._store = store
        self._filters = AuditQueryFilters()
        self._limit = 100
        self._offset = 0

    def for_entity(self, entity_type: str, entity_id: str) -> "AuditQuery[T]":
        """Filter by entity."""
        self._filters.entity_type = entity_type
        self._filters.entity_id = entity_id
        return self

    def by_user(self, user_id: str) -> "AuditQuery[T]":
        """Filter by user."""
        self._filters.user_id = user_id
        return self

    def with_action(self, action: AuditAction) -> "AuditQuery[T]":
        """Filter by action."""
        self._filters.action = action
        return self

    def with_correlation(self, correlation_id: str) -> "AuditQuery[T]":
        """Filter by correlation ID."""
        self._filters.correlation_id = correlation_id
        return self

    def between(
        self,
        start: datetime,
        end: datetime,
    ) -> "AuditQuery[T]":
        """Filter by date range."""
        self._filters.start_date = start
        self._filters.end_date = end
        return self

    def limit(self, count: int) -> "AuditQuery[T]":
        """Set result limit."""
        self._limit = count
        return self

    def offset(self, count: int) -> "AuditQuery[T]":
        """Set result offset."""
        self._offset = count
        return self

    async def execute(self) -> Sequence[AuditRecord[T]]:
        """Execute the query."""
        if self._filters.correlation_id:
            return await self._store.get_by_correlation(self._filters.correlation_id)
        if self._filters.entity_type and self._filters.entity_id:
            return await self._store.get_by_entity(
                self._filters.entity_type,
                self._filters.entity_id,
                limit=self._limit,
            )
        if self._filters.user_id:
            return await self._store.get_by_user(
                self._filters.user_id,
                limit=self._limit,
            )
        return []


class ExportFormat(Enum):
    """Audit export formats."""

    JSON = "json"
    CSV = "csv"
    XML = "xml"


@runtime_checkable
class AuditExporter[TFormat](Protocol):
    """Generic audit exporter for compliance reports.

    Type Parameters:
        TFormat: Export format configuration type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.5**
    """

    def export(
        self,
        records: Sequence[AuditRecord[Any]],
        format_config: TFormat,
    ) -> bytes:
        """Export audit records.

        Args:
            records: Records to export.
            format_config: Format-specific configuration.

        Returns:
            Exported data as bytes.
        """
        ...


@dataclass
class JsonExportConfig:
    """JSON export configuration."""

    pretty: bool = True
    include_metadata: bool = True


class JsonAuditExporter:
    """JSON audit exporter.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.5**
    """

    def export(
        self,
        records: Sequence[AuditRecord[Any]],
        format_config: JsonExportConfig | None = None,
    ) -> bytes:
        """Export records as JSON."""
        config = format_config or JsonExportConfig()
        data = [r.to_dict() for r in records]

        if not config.include_metadata:
            for record in data:
                record.pop("metadata", None)

        indent = 2 if config.pretty else None
        return json.dumps(data, indent=indent, default=str).encode("utf-8")


@dataclass
class CsvExportConfig:
    """CSV export configuration."""

    delimiter: str = ","
    include_header: bool = True


class CsvAuditExporter:
    """CSV audit exporter.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.5**
    """

    def export(
        self,
        records: Sequence[AuditRecord[Any]],
        format_config: CsvExportConfig | None = None,
    ) -> bytes:
        """Export records as CSV."""
        config = format_config or CsvExportConfig()

        if not records:
            return b""

        # Get headers from first record
        first_dict = records[0].to_dict()
        headers = list(first_dict.keys())

        lines = []
        if config.include_header:
            lines.append(config.delimiter.join(headers))

        for record in records:
            record_dict = record.to_dict()
            values = [str(record_dict.get(h, "")) for h in headers]
            lines.append(config.delimiter.join(values))

        return "\n".join(lines).encode("utf-8")
