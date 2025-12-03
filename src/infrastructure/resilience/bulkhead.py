"""Bulkhead pattern implementation.

**Feature: infrastructure-modules-workflow-analysis**
**Validates: Requirements 1.3**

This module provides bulkhead pattern for resource isolation.
"""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from core.base.patterns.result import Err, Ok, Result


class BulkheadRejectedError(Exception):
    """Raised when bulkhead rejects a request."""
    pass


class BulkheadState(Enum):
    """Bulkhead states."""
    ACCEPTING = "accepting"
    REJECTING = "rejecting"


@dataclass
class BulkheadStats:
    """Statistics for a bulkhead."""
    name: str
    max_concurrent: int
    current_concurrent: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_rejected: int = 0

    @property
    def available_permits(self) -> int:
        """Get available permits."""
        return self.max_concurrent - self.current_concurrent

    @property
    def utilization(self) -> float:
        """Get utilization ratio."""
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
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_rejected": self.total_rejected,
            "success_rate": self.success_rate,
        }


@dataclass
class BulkheadConfig:
    """Bulkhead configuration."""
    max_concurrent: int = 10
    max_wait_seconds: float = 5.0


T = TypeVar("T")


class Bulkhead:
    """Bulkhead for resource isolation.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 1.3**
    """

    def __init__(
        self,
        name: str,
        max_concurrent: int = 10,
        max_wait_seconds: float = 5.0,
    ) -> None:
        self.name = name
        self._max_concurrent = max_concurrent
        self._max_wait_seconds = max_wait_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._stats = BulkheadStats(name=name, max_concurrent=max_concurrent)
        self._lock = asyncio.Lock()

    @property
    def stats(self) -> BulkheadStats:
        """Get bulkhead statistics."""
        return self._stats

    @property
    def state(self) -> BulkheadState:
        """Get current state."""
        if self._stats.current_concurrent >= self._max_concurrent:
            return BulkheadState.REJECTING
        return BulkheadState.ACCEPTING

    async def acquire(self) -> bool:
        """Acquire a permit."""
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self._max_wait_seconds,
            )
            if acquired:
                async with self._lock:
                    self._stats.current_concurrent += 1
                return True
            return False
        except asyncio.TimeoutError:
            async with self._lock:
                self._stats.total_rejected += 1
            return False

    async def release(self) -> None:
        """Release a permit."""
        self._semaphore.release()
        async with self._lock:
            self._stats.current_concurrent = max(0, self._stats.current_concurrent - 1)

    @asynccontextmanager
    async def acquire_context(self):
        """Context manager for acquiring/releasing permits."""
        acquired = await self.acquire()
        if not acquired:
            raise BulkheadRejectedError(f"Bulkhead '{self.name}' rejected request")
        try:
            yield
            async with self._lock:
                self._stats.total_completed += 1
        except Exception:
            async with self._lock:
                self._stats.total_failed += 1
            raise
        finally:
            await self.release()

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function within bulkhead."""
        async with self.acquire_context():
            return await func(*args, **kwargs)


class BulkheadRegistry:
    """Registry for managing multiple bulkheads."""

    def __init__(self) -> None:
        self._bulkheads: dict[str, Bulkhead] = {}

    def register(
        self,
        name: str,
        max_concurrent: int = 10,
        max_wait_seconds: float = 5.0,
    ) -> Bulkhead:
        """Register a new bulkhead."""
        bulkhead = Bulkhead(name, max_concurrent, max_wait_seconds)
        self._bulkheads[name] = bulkhead
        return bulkhead

    def get(self, name: str) -> Bulkhead | None:
        """Get bulkhead by name."""
        return self._bulkheads.get(name)

    def get_or_create(
        self,
        name: str,
        max_concurrent: int = 10,
        max_wait_seconds: float = 5.0,
    ) -> Bulkhead:
        """Get existing or create new bulkhead."""
        if name in self._bulkheads:
            return self._bulkheads[name]
        return self.register(name, max_concurrent, max_wait_seconds)

    def list_names(self) -> list[str]:
        """List all bulkhead names."""
        return list(self._bulkheads.keys())

    def get_all_stats(self) -> dict[str, BulkheadStats]:
        """Get stats for all bulkheads."""
        return {name: b.stats for name, b in self._bulkheads.items()}


def bulkhead(
    name: str,
    max_concurrent: int = 10,
    max_wait_seconds: float = 5.0,
    registry: BulkheadRegistry | None = None,
):
    """Decorator to apply bulkhead to async function."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        _registry = registry or BulkheadRegistry()
        _bulkhead = _registry.get_or_create(name, max_concurrent, max_wait_seconds)

        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await _bulkhead.execute(func, *args, **kwargs)

        return wrapper
    return decorator


__all__ = [
    "Bulkhead",
    "BulkheadConfig",
    "BulkheadRejectedError",
    "BulkheadRegistry",
    "BulkheadState",
    "BulkheadStats",
    "bulkhead",
]
