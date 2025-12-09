"""Outbox repository for message persistence.

**Feature: python-api-base-2025-validation**
**Validates: Requirements 33.1, 33.2**
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from infrastructure.messaging.outbox.outbox_message import (
    OutboxMessage,
    OutboxMessageStatus,
)


class OutboxRepository:
    """In-memory outbox repository for testing and development.

    Warning:
        This is a TESTING/DEVELOPMENT implementation only!
        Messages are lost on application restart.

    For PRODUCTION, implement a database-backed repository that:
    1. Uses SQLModel/SQLAlchemy for persistence
    2. Stores messages in the SAME transaction as domain changes
    3. Includes proper indexes on (status, created_at) and idempotency_key

    Example production implementation:
        class SQLModelOutboxRepository(OutboxRepository):
            def __init__(self, session: AsyncSession):
                self._session = session
            # ... implement methods using SQLModel

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 33.1, 33.2**
    """

    def __init__(self) -> None:
        """Initialize outbox repository."""
        self._messages: dict[UUID, OutboxMessage] = {}
        self._processed_keys: set[str] = set()

    async def save(self, message: OutboxMessage) -> OutboxMessage:
        """Save outbox message.

        Args:
            message: Message to save.

        Returns:
            Saved message.
        """
        self._messages[message.id] = message
        return message

    async def save_many(self, messages: Sequence[OutboxMessage]) -> Sequence[OutboxMessage]:
        """Save multiple outbox messages.

        Args:
            messages: Messages to save.

        Returns:
            Saved messages.
        """
        for msg in messages:
            self._messages[msg.id] = msg
        return messages

    async def get_by_id(self, message_id: UUID) -> OutboxMessage | None:
        """Get message by ID.

        Args:
            message_id: Message identifier.

        Returns:
            Message if found, None otherwise.
        """
        return self._messages.get(message_id)

    async def get_pending(
        self,
        limit: int = 100,
        include_failed: bool = True,
    ) -> Sequence[OutboxMessage]:
        """Get pending messages ready for publishing.

        Args:
            limit: Maximum messages to return.
            include_failed: Include failed messages ready for retry.

        Returns:
            List of pending messages.
        """
        now = datetime.now(UTC)
        pending: list[OutboxMessage] = []

        for msg in self._messages.values():
            if len(pending) >= limit:
                break

            if msg.status == OutboxMessageStatus.PENDING:
                pending.append(msg)
            elif include_failed and msg.status == OutboxMessageStatus.FAILED:
                if msg.is_ready_for_retry:
                    pending.append(msg)

        # Sort by created_at for FIFO processing
        pending.sort(key=lambda m: m.created_at)
        return pending[:limit]

    async def update(self, message: OutboxMessage) -> OutboxMessage:
        """Update outbox message.

        Args:
            message: Message to update.

        Returns:
            Updated message.
        """
        self._messages[message.id] = message
        return message

    async def mark_processed(self, message_id: UUID) -> bool:
        """Mark message as processed.

        Args:
            message_id: Message identifier.

        Returns:
            True if marked, False if not found.
        """
        msg = self._messages.get(message_id)
        if msg is None:
            return False

        msg.mark_published()

        # Track idempotency key
        if msg.idempotency_key:
            self._processed_keys.add(msg.idempotency_key)

        return True

    async def mark_failed(
        self,
        message_id: UUID,
        error: str,
        next_retry: datetime | None = None,
    ) -> bool:
        """Mark message as failed.

        Args:
            message_id: Message identifier.
            error: Error message.
            next_retry: When to retry next.

        Returns:
            True if marked, False if not found.
        """
        msg = self._messages.get(message_id)
        if msg is None:
            return False

        msg.mark_failed(error, next_retry)
        return True

    async def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if message with idempotency key was already processed.

        Args:
            idempotency_key: Idempotency key to check.

        Returns:
            True if already processed, False otherwise.
        """
        return idempotency_key in self._processed_keys

    async def get_dead_letters(self, limit: int = 100) -> Sequence[OutboxMessage]:
        """Get messages in dead letter status.

        Args:
            limit: Maximum messages to return.

        Returns:
            List of dead letter messages.
        """
        dead_letters = [
            msg
            for msg in self._messages.values()
            if msg.status == OutboxMessageStatus.DEAD_LETTER
        ]
        dead_letters.sort(key=lambda m: m.created_at)
        return dead_letters[:limit]

    async def delete(self, message_id: UUID) -> bool:
        """Delete message.

        Args:
            message_id: Message identifier.

        Returns:
            True if deleted, False if not found.
        """
        if message_id in self._messages:
            del self._messages[message_id]
            return True
        return False

    async def cleanup_processed(self, older_than: datetime) -> int:
        """Clean up old processed messages.

        Args:
            older_than: Delete messages processed before this time.

        Returns:
            Number of messages deleted.
        """
        to_delete = [
            msg_id
            for msg_id, msg in self._messages.items()
            if msg.status == OutboxMessageStatus.PUBLISHED
            and msg.processed_at
            and msg.processed_at < older_than
        ]

        for msg_id in to_delete:
            del self._messages[msg_id]

        return len(to_delete)

    def clear(self) -> None:
        """Clear all messages (for testing)."""
        self._messages.clear()
        self._processed_keys.clear()
