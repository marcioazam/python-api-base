"""Lock manager for per-identifier locking in auto-ban system.

**Feature: shared-modules-refactoring**
**Validates: Requirements 2.1, 2.3, 2.4**

Provides thread-safe per-identifier locking to prevent race conditions
when recording violations and checking ban status.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Protocol
from collections.abc import AsyncIterator

from my_api.shared.exceptions import LockAcquisitionTimeout

logger = logging.getLogger(__name__)


class LockManager(Protocol):
    """Protocol for managing per-identifier locks."""

    @asynccontextmanager
    async def acquire(
        self,
        identifier: str,
        timeout: float = 5.0,
    ) -> AsyncIterator[None]:
        """Acquire a lock for the given identifier.

        Args:
            identifier: The identifier to lock.
            timeout: Maximum time to wait for lock acquisition.

        Yields:
            None when lock is acquired.

        Raises:
            LockAcquisitionTimeout: If lock cannot be acquired within timeout.
        """
        ...

    async def cleanup_stale(self, max_entries: int = 10000) -> int:
        """Clean up stale locks to prevent memory leaks.

        Args:
            max_entries: Maximum number of lock entries to keep.

        Returns:
            Number of entries removed.
        """
        ...


class InMemoryLockManager:
    """In-memory implementation of LockManager with automatic cleanup.

    Provides per-identifier locking using asyncio.Lock instances.
    Tracks last usage time for each lock to enable cleanup of stale entries.
    """

    def __init__(self) -> None:
        """Initialize the lock manager."""
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_used: dict[str, float] = {}
        self._manager_lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(
        self,
        identifier: str,
        timeout: float = 5.0,
    ) -> AsyncIterator[None]:
        """Acquire a lock for the given identifier.

        Args:
            identifier: The identifier to lock.
            timeout: Maximum time to wait for lock acquisition.

        Yields:
            None when lock is acquired.

        Raises:
            LockAcquisitionTimeout: If lock cannot be acquired within timeout.
        """
        async with self._manager_lock:
            if identifier not in self._locks:
                self._locks[identifier] = asyncio.Lock()

            lock = self._locks[identifier]

        try:
            acquired = await asyncio.wait_for(
                lock.acquire(),
                timeout=timeout,
            )
            if not acquired:
                logger.warning(
                    "Lock acquisition failed",
                    extra={"identifier": identifier, "timeout": timeout},
                )
                raise LockAcquisitionTimeout(identifier, timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "Lock acquisition timed out",
                extra={"identifier": identifier, "timeout": timeout},
            )
            raise LockAcquisitionTimeout(identifier, timeout)

        try:
            self._last_used[identifier] = asyncio.get_running_loop().time()
            yield
        finally:
            lock.release()

    async def cleanup_stale(self, max_entries: int = 10000) -> int:
        """Clean up stale locks to prevent memory leaks.

        Removes the oldest locks when the number of entries exceeds max_entries.
        Only removes locks that are not currently held.

        Args:
            max_entries: Maximum number of lock entries to keep.

        Returns:
            Number of entries removed.
        """
        async with self._manager_lock:
            if len(self._locks) <= max_entries:
                return 0

            # Sort by last used time (oldest first)
            sorted_identifiers = sorted(
                self._last_used.keys(),
                key=lambda k: self._last_used.get(k, 0),
            )

            removed = 0
            target_removals = len(self._locks) - max_entries

            for identifier in sorted_identifiers:
                if removed >= target_removals:
                    break

                lock = self._locks.get(identifier)
                if lock and not lock.locked():
                    del self._locks[identifier]
                    self._last_used.pop(identifier, None)
                    removed += 1

            if removed > 0:
                logger.info(
                    "Cleaned up stale locks",
                    extra={"removed": removed, "remaining": len(self._locks)},
                )

            return removed

    @property
    def lock_count(self) -> int:
        """Get the current number of locks."""
        return len(self._locks)
