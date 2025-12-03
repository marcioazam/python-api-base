"""Audit storage protocol and implementations.

**Feature: python-api-base-2025-generics-audit**
**Requirement: R22.2 - Generic audit store protocol for multiple backends**
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from infrastructure.audit.trail import AuditRecord


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
