"""Inbox Pattern implementation for idempotent message processing.

Ensures messages are processed exactly once using an inbox table.

**Feature: api-architecture-analysis, Property 9: Inbox pattern**
**Validates: Requirements 9.5**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable
import hashlib
import json


class InboxStatus(str, Enum):
    """Status of an inbox entry."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass(slots=True)
class InboxEntry:
    """An entry in the inbox table."""

    message_id: str
    message_type: str
    payload: dict[str, Any]
    status: InboxStatus = InboxStatus.PENDING
    received_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None
    error_message: str | None = None
    idempotency_key: str | None = None

    @classmethod
    def create(
        cls,
        message_id: str,
        message_type: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> "InboxEntry":
        """Create a new inbox entry."""
        return cls(
            message_id=message_id,
            message_type=message_type,
            payload=payload,
            idempotency_key=idempotency_key or cls._generate_idempotency_key(
                message_id, message_type, payload
            ),
        )

    @staticmethod
    def _generate_idempotency_key(
        message_id: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Generate idempotency key from message content."""
        content = f"{message_id}:{message_type}:{json.dumps(payload, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def mark_processing(self) -> None:
        """Mark entry as processing."""
        self.status = InboxStatus.PROCESSING

    def mark_processed(self) -> None:
        """Mark entry as processed."""
        self.status = InboxStatus.PROCESSED
        self.processed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        """Mark entry as failed."""
        self.status = InboxStatus.FAILED
        self.error_message = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "payload": self.payload,
            "status": self.status.value,
            "received_at": self.received_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_message": self.error_message,
            "idempotency_key": self.idempotency_key,
        }


@runtime_checkable
class MessageHandler(Protocol):
    """Protocol for message handlers."""

    async def handle(self, message_type: str, payload: dict[str, Any]) -> None:
        """Handle a message."""
        ...


@runtime_checkable
class InboxRepository(Protocol):
    """Protocol for inbox repository."""

    async def save(self, entry: InboxEntry) -> None:
        """Save an inbox entry."""
        ...

    async def get_by_id(self, message_id: str) -> InboxEntry | None:
        """Get entry by message ID."""
        ...

    async def get_by_idempotency_key(self, key: str) -> InboxEntry | None:
        """Get entry by idempotency key."""
        ...

    async def update(self, entry: InboxEntry) -> None:
        """Update an inbox entry."""
        ...

    async def delete_processed(self, older_than: datetime) -> int:
        """Delete processed entries older than given date."""
        ...


class InMemoryInboxRepository:
    """In-memory implementation of inbox repository."""

    def __init__(self):
        self._entries: dict[str, InboxEntry] = {}
        self._by_idempotency_key: dict[str, str] = {}

    async def save(self, entry: InboxEntry) -> None:
        """Save an inbox entry."""
        self._entries[entry.message_id] = entry
        if entry.idempotency_key:
            self._by_idempotency_key[entry.idempotency_key] = entry.message_id

    async def get_by_id(self, message_id: str) -> InboxEntry | None:
        """Get entry by message ID."""
        return self._entries.get(message_id)

    async def get_by_idempotency_key(self, key: str) -> InboxEntry | None:
        """Get entry by idempotency key."""
        message_id = self._by_idempotency_key.get(key)
        if message_id:
            return self._entries.get(message_id)
        return None

    async def update(self, entry: InboxEntry) -> None:
        """Update an inbox entry."""
        self._entries[entry.message_id] = entry

    async def delete_processed(self, older_than: datetime) -> int:
        """Delete processed entries older than given date."""
        to_delete = [
            e.message_id for e in self._entries.values()
            if e.status == InboxStatus.PROCESSED
            and e.processed_at
            and e.processed_at < older_than
        ]
        for message_id in to_delete:
            entry = self._entries.pop(message_id, None)
            if entry and entry.idempotency_key:
                self._by_idempotency_key.pop(entry.idempotency_key, None)
        return len(to_delete)

    def count(self) -> int:
        """Get total count of entries."""
        return len(self._entries)


class InboxService:
    """Service for managing the inbox pattern."""

    def __init__(self, repository: InboxRepository, handler: MessageHandler):
        self._repository = repository
        self._handler = handler

    async def receive(
        self,
        message_id: str,
        message_type: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> tuple[bool, InboxEntry]:
        """Receive and process a message. Returns (is_new, entry)."""
        entry = InboxEntry.create(
            message_id=message_id,
            message_type=message_type,
            payload=payload,
            idempotency_key=idempotency_key,
        )

        existing = await self._repository.get_by_idempotency_key(
            entry.idempotency_key or ""
        )
        if existing:
            return False, existing

        await self._repository.save(entry)
        return True, entry

    async def process(self, entry: InboxEntry) -> bool:
        """Process an inbox entry. Returns True if successful."""
        if entry.status != InboxStatus.PENDING:
            return entry.status == InboxStatus.PROCESSED

        entry.mark_processing()
        await self._repository.update(entry)

        try:
            await self._handler.handle(entry.message_type, entry.payload)
            entry.mark_processed()
            await self._repository.update(entry)
            return True
        except Exception as e:
            entry.mark_failed(str(e))
            await self._repository.update(entry)
            return False

    async def receive_and_process(
        self,
        message_id: str,
        message_type: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> tuple[bool, bool]:
        """Receive and process a message. Returns (is_new, success)."""
        is_new, entry = await self.receive(
            message_id, message_type, payload, idempotency_key
        )
        if not is_new:
            return False, entry.status == InboxStatus.PROCESSED

        success = await self.process(entry)
        return True, success

    async def cleanup(self, older_than: datetime) -> int:
        """Clean up old processed entries."""
        return await self._repository.delete_processed(older_than)

    async def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if a message is a duplicate."""
        entry = await self._repository.get_by_idempotency_key(idempotency_key)
        return entry is not None


class MockMessageHandler:
    """Mock message handler for testing."""

    def __init__(self, should_fail: bool = False):
        self._should_fail = should_fail
        self._handled: list[tuple[str, dict[str, Any]]] = []

    async def handle(self, message_type: str, payload: dict[str, Any]) -> None:
        """Handle a message."""
        if self._should_fail:
            raise RuntimeError("Handler failed")
        self._handled.append((message_type, payload))

    @property
    def handled_messages(self) -> list[tuple[str, dict[str, Any]]]:
        """Get list of handled messages."""
        return self._handled.copy()

    def clear(self) -> None:
        """Clear handled messages."""
        self._handled.clear()
