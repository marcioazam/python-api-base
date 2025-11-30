"""Long Polling support for legacy clients.

Implements long polling pattern for clients that don't support WebSockets.

**Feature: api-architecture-analysis, Property 4: Long polling support**
**Validates: Requirements 4.5**
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any
import uuid


class PollStatus(str, Enum):
    """Status of a poll request."""

    PENDING = "pending"
    DATA_AVAILABLE = "data_available"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass(slots=True)
class PollResult[T]:
    """Result of a poll request."""

    status: PollStatus
    data: T | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def success(cls, data: T) -> "PollResult[T]":
        """Create a success result."""
        return cls(status=PollStatus.DATA_AVAILABLE, data=data)

    @classmethod
    def timeout(cls) -> "PollResult[T]":
        """Create a timeout result."""
        return cls(status=PollStatus.TIMEOUT)

    @classmethod
    def failure(cls, error: str) -> "PollResult[T]":
        """Create an error result."""
        return cls(status=PollStatus.ERROR, error=error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass(slots=True)
class PollConfig:
    """Configuration for long polling."""

    timeout_seconds: float = 30.0
    max_timeout_seconds: float = 60.0
    min_timeout_seconds: float = 5.0
    poll_interval_seconds: float = 0.1
    max_events_per_poll: int = 100

    def validate_timeout(self, timeout: float) -> float:
        """Validate and clamp timeout value."""
        return max(self.min_timeout_seconds, min(timeout, self.max_timeout_seconds))


class EventQueue[T]:
    """Queue for events to be delivered via long polling."""

    def __init__(self, max_size: int = 1000) -> None:
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=max_size)
        self._subscribers: dict[str, asyncio.Event] = {}

    async def publish(self, event: T) -> None:
        """Publish an event to the queue."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            await self._queue.get()
            await self._queue.put(event)

        for notify_event in self._subscribers.values():
            notify_event.set()

    async def subscribe(self, subscriber_id: str) -> None:
        """Subscribe to events."""
        self._subscribers[subscriber_id] = asyncio.Event()

    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from events."""
        self._subscribers.pop(subscriber_id, None)

    async def wait_for_event(
        self, subscriber_id: str, timeout: float
    ) -> T | None:
        """Wait for an event with timeout."""
        notify_event = self._subscribers.get(subscriber_id)
        if notify_event is None:
            return None

        try:
            await asyncio.wait_for(notify_event.wait(), timeout=timeout)
            notify_event.clear()
            if not self._queue.empty():
                return await self._queue.get()
        except asyncio.TimeoutError:
            pass
        return None

    def get_pending_count(self) -> int:
        """Get count of pending events."""
        return self._queue.qsize()

    def clear(self) -> None:
        """Clear all pending events."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


class LongPollEndpoint[T]:
    """Long polling endpoint handler."""

    def __init__(self, config: PollConfig | None = None) -> None:
        self._config = config or PollConfig()
        self._queues: dict[str, EventQueue[T]] = {}
        self._sessions: dict[str, datetime] = {}

    def create_session(self) -> str:
        """Create a new polling session."""
        session_id = str(uuid.uuid4())
        self._queues[session_id] = EventQueue()
        self._sessions[session_id] = datetime.now(UTC)
        return session_id

    def close_session(self, session_id: str) -> bool:
        """Close a polling session."""
        if session_id in self._queues:
            del self._queues[session_id]
            del self._sessions[session_id]
            return True
        return False

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return session_id in self._queues

    async def publish(self, session_id: str, event: T) -> bool:
        """Publish an event to a session."""
        queue = self._queues.get(session_id)
        if queue is None:
            return False
        await queue.publish(event)
        return True

    async def broadcast(self, event: T) -> int:
        """Broadcast an event to all sessions."""
        count = 0
        for queue in self._queues.values():
            await queue.publish(event)
            count += 1
        return count

    async def poll(
        self, session_id: str, timeout: float | None = None
    ) -> PollResult[T]:
        """Poll for events."""
        queue = self._queues.get(session_id)
        if queue is None:
            return PollResult.failure("Session not found")

        actual_timeout = self._config.validate_timeout(
            timeout or self._config.timeout_seconds
        )

        subscriber_id = str(uuid.uuid4())
        await queue.subscribe(subscriber_id)

        try:
            event = await queue.wait_for_event(subscriber_id, actual_timeout)
            if event is not None:
                return PollResult.success(event)
            return PollResult.timeout()
        finally:
            queue.unsubscribe(subscriber_id)

    async def poll_batch(
        self, session_id: str, timeout: float | None = None
    ) -> PollResult[list[T]]:
        """Poll for multiple events."""
        queue = self._queues.get(session_id)
        if queue is None:
            return PollResult.failure("Session not found")

        actual_timeout = self._config.validate_timeout(
            timeout or self._config.timeout_seconds
        )

        events: list[T] = []
        end_time = datetime.now(UTC) + timedelta(seconds=actual_timeout)

        while datetime.now(UTC) < end_time:
            if queue.get_pending_count() > 0:
                while (
                    queue.get_pending_count() > 0
                    and len(events) < self._config.max_events_per_poll
                ):
                    try:
                        event = await asyncio.wait_for(
                            queue._queue.get(), timeout=0.1
                        )
                        events.append(event)
                    except asyncio.TimeoutError:
                        break
                if events:
                    return PollResult.success(events)
            await asyncio.sleep(self._config.poll_interval_seconds)

        if events:
            return PollResult.success(events)
        return PollResult.timeout()

    def get_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)

    def cleanup_stale_sessions(self, max_age_seconds: float = 3600) -> int:
        """Clean up stale sessions."""
        now = datetime.now(UTC)
        stale = [
            sid
            for sid, created in self._sessions.items()
            if (now - created).total_seconds() > max_age_seconds
        ]
        for sid in stale:
            self.close_session(sid)
        return len(stale)
