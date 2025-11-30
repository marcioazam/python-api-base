"""Outbox Pattern implementation for reliable event publishing.

Ensures events are published reliably using transactional outbox.

**Feature: api-architecture-analysis, Property 7: Outbox pattern**
**Validates: Requirements 9.5**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable
import json
import uuid


class OutboxStatus(str, Enum):
    """Status of an outbox entry."""

    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass(slots=True)
class OutboxEntry:
    """An entry in the outbox table."""

    id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict[str, Any]
    status: OutboxStatus = OutboxStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None

    @classmethod
    def create(
        cls,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> "OutboxEntry":
        """Create a new outbox entry."""
        return cls(
            id=str(uuid.uuid4()),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    def mark_processing(self) -> None:
        """Mark entry as processing."""
        self.status = OutboxStatus.PROCESSING

    def mark_published(self) -> None:
        """Mark entry as published."""
        self.status = OutboxStatus.PUBLISHED
        self.processed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        """Mark entry as failed."""
        self.retry_count += 1
        self.error_message = error
        if self.retry_count >= self.max_retries:
            self.status = OutboxStatus.FAILED
        else:
            self.status = OutboxStatus.PENDING

    @property
    def can_retry(self) -> bool:
        """Check if entry can be retried."""
        return self.retry_count < self.max_retries


@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for event publishers."""

    async def publish(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Publish an event."""
        ...


@runtime_checkable
class OutboxRepository(Protocol):
    """Protocol for outbox repository."""

    async def save(self, entry: OutboxEntry) -> None:
        """Save an outbox entry."""
        ...

    async def get_pending(self, limit: int = 100) -> list[OutboxEntry]:
        """Get pending entries."""
        ...

    async def update(self, entry: OutboxEntry) -> None:
        """Update an outbox entry."""
        ...

    async def delete_published(self, older_than: datetime) -> int:
        """Delete published entries older than given date."""
        ...


class InMemoryOutboxRepository:
    """In-memory implementation of outbox repository."""

    def __init__(self):
        self._entries: dict[str, OutboxEntry] = {}

    async def save(self, entry: OutboxEntry) -> None:
        """Save an outbox entry."""
        self._entries[entry.id] = entry

    async def get_pending(self, limit: int = 100) -> list[OutboxEntry]:
        """Get pending entries."""
        pending = [
            e for e in self._entries.values()
            if e.status == OutboxStatus.PENDING
        ]
        return sorted(pending, key=lambda e: e.created_at)[:limit]

    async def update(self, entry: OutboxEntry) -> None:
        """Update an outbox entry."""
        self._entries[entry.id] = entry

    async def delete_published(self, older_than: datetime) -> int:
        """Delete published entries older than given date."""
        to_delete = [
            e.id for e in self._entries.values()
            if e.status == OutboxStatus.PUBLISHED
            and e.processed_at
            and e.processed_at < older_than
        ]
        for entry_id in to_delete:
            del self._entries[entry_id]
        return len(to_delete)

    def count(self) -> int:
        """Get total count of entries."""
        return len(self._entries)

    def count_by_status(self, status: OutboxStatus) -> int:
        """Get count of entries by status."""
        return sum(1 for e in self._entries.values() if e.status == status)


class OutboxService:
    """Service for managing the outbox pattern."""

    def __init__(
        self,
        repository: OutboxRepository,
        publisher: EventPublisher,
        batch_size: int = 100,
    ):
        self._repository = repository
        self._publisher = publisher
        self._batch_size = batch_size

    async def add_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> OutboxEntry:
        """Add an event to the outbox."""
        entry = OutboxEntry.create(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
        )
        await self._repository.save(entry)
        return entry

    async def process_pending(self) -> tuple[int, int]:
        """Process pending outbox entries. Returns (success, failed) counts."""
        entries = await self._repository.get_pending(self._batch_size)
        success_count = 0
        failed_count = 0

        for entry in entries:
            entry.mark_processing()
            await self._repository.update(entry)

            try:
                published = await self._publisher.publish(
                    entry.event_type, entry.payload
                )
                if published:
                    entry.mark_published()
                    success_count += 1
                else:
                    entry.mark_failed("Publisher returned False")
                    failed_count += 1
            except Exception as e:
                entry.mark_failed(str(e))
                failed_count += 1

            await self._repository.update(entry)

        return success_count, failed_count

    async def cleanup(self, older_than: datetime) -> int:
        """Clean up old published entries."""
        return await self._repository.delete_published(older_than)


class MockEventPublisher:
    """Mock event publisher for testing."""

    def __init__(self, should_fail: bool = False):
        self._should_fail = should_fail
        self._published: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Publish an event."""
        if self._should_fail:
            return False
        self._published.append((event_type, payload))
        return True

    @property
    def published_events(self) -> list[tuple[str, dict[str, Any]]]:
        """Get list of published events."""
        return self._published.copy()

    def clear(self) -> None:
        """Clear published events."""
        self._published.clear()
