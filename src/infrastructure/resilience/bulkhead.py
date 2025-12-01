"""Bulkhead Pattern implementation for resource isolation.

Provides resource isolation to prevent cascading failures.

**Feature: api-architecture-analysis, Property 10: Bulkhead pattern**
**Validates: Requirements 6.1**
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any
from collections.abc import AsyncIterator
from collections.abc import Callable, Awaitable
import functools


class BulkheadState(str, Enum):
    """State of a bulkhead."""

    ACCEPTING = "accepting"
    REJECTING = "rejecting"


class BulkheadRejectedError(Exception):
    """Raised when bulkhead rejects a request."""

    def __init__(self, name: str, reason: str):
        self.name = name
        self.reason = reason
        super().__init__(f"Bulkhead '{name}' rejected: {reason}")


@dataclass(slots=True)
class BulkheadStats:
    """Statistics for a bulkhead."""

    name: str
    max_concurrent: int
    current_concurrent: int
    total_accepted: int = 0
    total_rejected: int = 0
    total_completed: int = 0
    total_failed: int = 0

    @property
    def available_permits(self) -> int:
        """Get number of available permits."""
        return max(0, self.max_concurrent - self.current_concurrent)

    @property
    def utilization(self) -> float:
        """Get current utilization percentage."""
        if self.max_concurrent == 0:
            return 0.0
        return self.current_concurrent / self.max_concurrent

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        total = self.total_completed + self.total_failed
        if total == 0:
            return 1.0
        return self.total_completed / total

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "current_concurrent": self.current_concurrent,
            "available_permits": self.available_permits,
            "utilization": self.utilization,
            "total_accepted": self.total_accepted,
            "total_rejected": self.total_rejected,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "success_rate": self.success_rate,
        }


class Bulkhead:
    """Semaphore-based bulkhead for limiting concurrent executions."""

    def __init__(
        self,
        name: str,
        max_concurrent: int,
        max_wait_seconds: float | None = None,
    ):
        self._name = name
        self._max_concurrent = max_concurrent
        self._max_wait = max_wait_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._current = 0
        self._stats = BulkheadStats(
            name=name,
            max_concurrent=max_concurrent,
            current_concurrent=0,
        )
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """Get bulkhead name."""
        return self._name

    @property
    def stats(self) -> BulkheadStats:
        """Get current statistics."""
        return self._stats

    @property
    def state(self) -> BulkheadState:
        """Get current state."""
        if self._stats.available_permits > 0:
            return BulkheadState.ACCEPTING
        return BulkheadState.REJECTING

    async def acquire(self) -> bool:
        """Acquire a permit. Returns True if acquired."""
        try:
            if self._max_wait is not None:
                acquired = await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=self._max_wait,
                )
            else:
                acquired = self._semaphore.acquire()
                if asyncio.iscoroutine(acquired):
                    acquired = await acquired
                else:
                    acquired = True

            async with self._lock:
                self._current += 1
                self._stats.current_concurrent = self._current
                self._stats.total_accepted += 1
            return True
        except asyncio.TimeoutError:
            async with self._lock:
                self._stats.total_rejected += 1
            return False

    async def release(self, success: bool = True) -> None:
        """Release a permit."""
        self._semaphore.release()
        async with self._lock:
            self._current -= 1
            self._stats.current_concurrent = self._current
            if success:
                self._stats.total_completed += 1
            else:
                self._stats.total_failed += 1

    @asynccontextmanager
    async def acquire_context(self) -> AsyncIterator[None]:
        """Context manager for acquiring and releasing."""
        acquired = await self.acquire()
        if not acquired:
            raise BulkheadRejectedError(self._name, "Timeout waiting for permit")
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            await self.release(success)

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function within the bulkhead."""
        async with self.acquire_context():
            return await func(*args, **kwargs)


class BulkheadRegistry:
    """Registry for managing multiple bulkheads."""

    def __init__(self):
        self._bulkheads: dict[str, Bulkhead] = {}

    def register(
        self,
        name: str,
        max_concurrent: int,
        max_wait_seconds: float | None = None,
    ) -> Bulkhead:
        """Register a new bulkhead."""
        bulkhead = Bulkhead(name, max_concurrent, max_wait_seconds)
        self._bulkheads[name] = bulkhead
        return bulkhead

    def get(self, name: str) -> Bulkhead | None:
        """Get a bulkhead by name."""
        return self._bulkheads.get(name)

    def get_or_create(
        self,
        name: str,
        max_concurrent: int = 10,
        max_wait_seconds: float | None = None,
    ) -> Bulkhead:
        """Get existing or create new bulkhead."""
        if name not in self._bulkheads:
            return self.register(name, max_concurrent, max_wait_seconds)
        return self._bulkheads[name]

    def list_names(self) -> list[str]:
        """List all bulkhead names."""
        return list(self._bulkheads.keys())

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get stats for all bulkheads."""
        return {name: b.stats.to_dict() for name, b in self._bulkheads.items()}


def bulkhead[T](
    name: str,
    max_concurrent: int = 10,
    max_wait_seconds: float | None = None,
    registry: BulkheadRegistry | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to apply bulkhead to an async function."""
    _registry = registry or BulkheadRegistry()

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        _bulkhead = _registry.get_or_create(name, max_concurrent, max_wait_seconds)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await _bulkhead.execute(func, *args, **kwargs)

        return wrapper

    return decorator
