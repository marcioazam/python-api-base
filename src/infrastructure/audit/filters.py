"""Audit query filters and export functionality.

**Feature: python-api-base-2025-generics-audit**
**Requirement: R22.3 - Generic audit query with typed filters**
**Requirement: R22.5 - Generic audit exporter for compliance reports**
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from infrastructure.audit.trail import AuditAction, AuditRecord
from infrastructure.audit.storage import AuditStore


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
