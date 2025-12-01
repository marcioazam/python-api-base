"""Distributed Locking implementation.

Provides distributed locking using Redis or in-memory for testing.

**Feature: api-architecture-analysis, Property 8: Distributed locking**
**Validates: Requirements 9.3**
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections.abc import AsyncIterator
import uuid


@dataclass(frozen=True, slots=True)
class LockInfo:
    """Information about an acquired lock."""

    key: str
    token: str
    acquired_at: datetime
    expires_at: datetime

    @property
    def ttl_seconds(self) -> float:
        """Get remaining TTL in seconds."""
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, remaining)

    @property
    def is_expired(self) -> bool:
        """Check if lock is expired."""
        return datetime.now(timezone.utc) >= self.expires_at


class LockAcquisitionError(Exception):
    """Raised when lock cannot be acquired."""

    pass


class LockRenewalError(Exception):
    """Raised when lock cannot be renewed."""

    pass


class DistributedLock(ABC):
    """Abstract base class for distributed locks."""

    @abstractmethod
    async def acquire(
        self,
        key: str,
        ttl_seconds: float = 30.0,
        wait_timeout: float | None = None,
    ) -> LockInfo:
        """Acquire a lock."""
        ...

    @abstractmethod
    async def release(self, lock_info: LockInfo) -> bool:
        """Release a lock."""
        ...

    @abstractmethod
    async def renew(self, lock_info: LockInfo, ttl_seconds: float = 30.0) -> LockInfo:
        """Renew a lock's TTL."""
        ...

    @abstractmethod
    async def is_locked(self, key: str) -> bool:
        """Check if a key is locked."""
        ...

    @asynccontextmanager
    async def lock(
        self,
        key: str,
        ttl_seconds: float = 30.0,
        wait_timeout: float | None = None,
    ) -> AsyncIterator[LockInfo]:
        """Context manager for acquiring and releasing a lock."""
        lock_info = await self.acquire(key, ttl_seconds, wait_timeout)
        try:
            yield lock_info
        finally:
            await self.release(lock_info)


@dataclass(slots=True)
class InMemoryLockEntry:
    """Entry for in-memory lock storage."""

    token: str
    expires_at: datetime


class InMemoryDistributedLock(DistributedLock):
    """In-memory implementation of distributed lock for testing."""

    def __init__(self):
        self._locks: dict[str, InMemoryLockEntry] = {}
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        key: str,
        ttl_seconds: float = 30.0,
        wait_timeout: float | None = None,
    ) -> LockInfo:
        """Acquire a lock."""
        start_time = datetime.now(timezone.utc)
        token = str(uuid.uuid4())

        while True:
            async with self._lock:
                self._cleanup_expired()

                if key not in self._locks:
                    now = datetime.now(timezone.utc)
                    expires_at = now + timedelta(seconds=ttl_seconds)
                    self._locks[key] = InMemoryLockEntry(token=token, expires_at=expires_at)
                    return LockInfo(
                        key=key,
                        token=token,
                        acquired_at=now,
                        expires_at=expires_at,
                    )

            if wait_timeout is None:
                raise LockAcquisitionError(f"Failed to acquire lock for key: {key}")

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= wait_timeout:
                raise LockAcquisitionError(
                    f"Timeout waiting for lock on key: {key}"
                )

            await asyncio.sleep(0.1)

    async def release(self, lock_info: LockInfo) -> bool:
        """Release a lock."""
        async with self._lock:
            entry = self._locks.get(lock_info.key)
            if entry is None:
                return False
            if entry.token != lock_info.token:
                return False
            del self._locks[lock_info.key]
            return True

    async def renew(self, lock_info: LockInfo, ttl_seconds: float = 30.0) -> LockInfo:
        """Renew a lock's TTL."""
        async with self._lock:
            entry = self._locks.get(lock_info.key)
            if entry is None:
                raise LockRenewalError(f"Lock not found for key: {lock_info.key}")
            if entry.token != lock_info.token:
                raise LockRenewalError(f"Token mismatch for key: {lock_info.key}")

            now = datetime.now(timezone.utc)
            new_expires_at = now + timedelta(seconds=ttl_seconds)
            entry.expires_at = new_expires_at

            return LockInfo(
                key=lock_info.key,
                token=lock_info.token,
                acquired_at=lock_info.acquired_at,
                expires_at=new_expires_at,
            )

    async def is_locked(self, key: str) -> bool:
        """Check if a key is locked."""
        async with self._lock:
            self._cleanup_expired()
            return key in self._locks

    def _cleanup_expired(self) -> None:
        """Remove expired locks."""
        now = datetime.now(timezone.utc)
        expired = [k for k, v in self._locks.items() if v.expires_at <= now]
        for key in expired:
            del self._locks[key]

    def get_lock_count(self) -> int:
        """Get count of active locks."""
        return len(self._locks)


class LockManager:
    """Manager for distributed locks with auto-renewal."""

    def __init__(self, lock: DistributedLock, renewal_interval: float = 10.0):
        self._lock = lock
        self._renewal_interval = renewal_interval
        self._renewal_tasks: dict[str, asyncio.Task[None]] = {}

    async def acquire_with_renewal(
        self,
        key: str,
        ttl_seconds: float = 30.0,
        wait_timeout: float | None = None,
    ) -> LockInfo:
        """Acquire a lock with automatic renewal."""
        lock_info = await self._lock.acquire(key, ttl_seconds, wait_timeout)
        self._start_renewal(lock_info, ttl_seconds)
        return lock_info

    async def release_with_renewal(self, lock_info: LockInfo) -> bool:
        """Release a lock and stop renewal."""
        self._stop_renewal(lock_info.key)
        return await self._lock.release(lock_info)

    def _start_renewal(self, lock_info: LockInfo, ttl_seconds: float) -> None:
        """Start automatic renewal task."""
        async def renewal_loop() -> None:
            current_info = lock_info
            while True:
                await asyncio.sleep(self._renewal_interval)
                try:
                    current_info = await self._lock.renew(current_info, ttl_seconds)
                except LockRenewalError:
                    break

        task = asyncio.create_task(renewal_loop())
        self._renewal_tasks[lock_info.key] = task

    def _stop_renewal(self, key: str) -> None:
        """Stop automatic renewal task."""
        task = self._renewal_tasks.pop(key, None)
        if task:
            task.cancel()

    @asynccontextmanager
    async def lock(
        self,
        key: str,
        ttl_seconds: float = 30.0,
        wait_timeout: float | None = None,
    ) -> AsyncIterator[LockInfo]:
        """Context manager with auto-renewal."""
        lock_info = await self.acquire_with_renewal(key, ttl_seconds, wait_timeout)
        try:
            yield lock_info
        finally:
            await self.release_with_renewal(lock_info)
