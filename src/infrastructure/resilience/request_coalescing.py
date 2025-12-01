"""Request coalescing for deduplicating concurrent identical requests.

**Feature: api-architecture-analysis, Task 12.2: Request Coalescing**
**Validates: Requirements 6.1**

Provides request deduplication to reduce load on backend services.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from collections.abc import Awaitable, Callable

from pydantic import BaseModel


class CoalescingStrategy(str, Enum):
    """Request coalescing strategies."""

    FIRST_WINS = "first_wins"  # First request executes, others wait
    DEBOUNCE = "debounce"  # Wait for quiet period before executing
    THROTTLE = "throttle"  # Execute at most once per interval


@dataclass
class CoalescingConfig:
    """Request coalescing configuration.

    Attributes:
        strategy: Coalescing strategy to use.
        window_ms: Deduplication window in milliseconds.
        max_wait_ms: Maximum wait time in milliseconds.
        max_coalesced: Maximum requests to coalesce.
        key_ttl_ms: TTL for request keys in milliseconds.
    """

    strategy: CoalescingStrategy = CoalescingStrategy.FIRST_WINS
    window_ms: int = 100
    max_wait_ms: int = 5000
    max_coalesced: int = 100
    key_ttl_ms: int = 10000


@dataclass
class PendingRequest[T]:
    """Pending coalesced request.

    Attributes:
        key: Request key.
        future: Future for the result.
        created_at: Request creation time.
        coalesced_count: Number of coalesced requests.
    """

    key: str
    future: asyncio.Future[T]
    created_at: float = field(default_factory=time.time)
    coalesced_count: int = 1


class CoalescingStats(BaseModel):
    """Coalescing statistics.

    Attributes:
        total_requests: Total requests received.
        coalesced_requests: Requests that were coalesced.
        executed_requests: Requests that were executed.
        cache_hits: Requests served from cache.
        avg_coalesced_per_request: Average coalesced per execution.
    """

    total_requests: int = 0
    coalesced_requests: int = 0
    executed_requests: int = 0
    cache_hits: int = 0
    avg_coalesced_per_request: float = 0.0


class RequestCoalescer[T]:
    """Request coalescer for deduplicating concurrent requests.

    Coalesces identical concurrent requests so only one actual
    execution happens, with all waiters receiving the same result.
    """

    def __init__(self, config: CoalescingConfig | None = None) -> None:
        """Initialize request coalescer.

        Args:
            config: Coalescing configuration.
        """
        self._config = config or CoalescingConfig()
        self._pending: dict[str, PendingRequest[T]] = {}
        self._cache: dict[str, tuple[T, float]] = {}
        self._lock = asyncio.Lock()
        self._stats = CoalescingStats()
        self._coalesced_counts: list[int] = []

    @staticmethod
    def generate_key(*args: Any, **kwargs: Any) -> str:
        """Generate a cache key from arguments.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Hash key for the request.
        """
        key_data = str((args, sorted(kwargs.items())))
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    async def execute(
        self,
        key: str,
        func: Callable[[], Awaitable[T]],
    ) -> T:
        """Execute a request with coalescing.

        Args:
            key: Request key for deduplication.
            func: Async function to execute.

        Returns:
            Result of the function.
        """
        self._stats.total_requests += 1

        # Check cache first
        if key in self._cache:
            result, cached_at = self._cache[key]
            if (time.time() - cached_at) * 1000 < self._config.key_ttl_ms:
                self._stats.cache_hits += 1
                return result

        async with self._lock:
            # Check if request is already pending
            if key in self._pending:
                pending = self._pending[key]
                if pending.coalesced_count < self._config.max_coalesced:
                    pending.coalesced_count += 1
                    self._stats.coalesced_requests += 1
                    return await pending.future

            # Create new pending request
            future: asyncio.Future[T] = asyncio.get_event_loop().create_future()
            pending = PendingRequest(key=key, future=future)
            self._pending[key] = pending

        # Execute the request
        try:
            if self._config.strategy == CoalescingStrategy.DEBOUNCE:
                await asyncio.sleep(self._config.window_ms / 1000)

            result = await func()

            # Cache result
            self._cache[key] = (result, time.time())

            # Update stats
            self._stats.executed_requests += 1
            self._coalesced_counts.append(pending.coalesced_count)
            if len(self._coalesced_counts) > 100:
                self._coalesced_counts.pop(0)
            self._stats.avg_coalesced_per_request = (
                sum(self._coalesced_counts) / len(self._coalesced_counts)
            )

            # Resolve future
            if not future.done():
                future.set_result(result)

            return result

        except Exception as e:
            if not future.done():
                future.set_exception(e)
            raise

        finally:
            async with self._lock:
                self._pending.pop(key, None)

    async def execute_with_args(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a request with automatic key generation.

        Args:
            func: Async function to execute.
            *args: Function arguments.
            **kwargs: Function keyword arguments.

        Returns:
            Result of the function.
        """
        key = self.generate_key(*args, **kwargs)
        return await self.execute(key, lambda: func(*args, **kwargs))

    def get_stats(self) -> CoalescingStats:
        """Get coalescing statistics.

        Returns:
            Current statistics.
        """
        return self._stats.model_copy()

    def clear_cache(self) -> int:
        """Clear the result cache.

        Returns:
            Number of entries cleared.
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def clear_expired_cache(self) -> int:
        """Clear expired cache entries.

        Returns:
            Number of entries cleared.
        """
        current_time = time.time()
        ttl_seconds = self._config.key_ttl_ms / 1000

        expired = [
            k for k, (_, cached_at) in self._cache.items()
            if current_time - cached_at > ttl_seconds
        ]

        for key in expired:
            del self._cache[key]

        return len(expired)

    @property
    def pending_count(self) -> int:
        """Get number of pending requests."""
        return len(self._pending)

    @property
    def cache_size(self) -> int:
        """Get cache size."""
        return len(self._cache)


def coalesce[T](
    key_func: Callable[..., str] | None = None,
    config: CoalescingConfig | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for request coalescing.

    Args:
        key_func: Function to generate cache key from arguments.
        config: Coalescing configuration.

    Returns:
        Decorator function.
    """
    coalescer: RequestCoalescer[Any] = RequestCoalescer(config)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = RequestCoalescer.generate_key(*args, **kwargs)

            return await coalescer.execute(key, lambda: func(*args, **kwargs))

        wrapper._coalescer = coalescer  # type: ignore
        return wrapper

    return decorator


class BatchCoalescer[T]:
    """Batch request coalescer.

    Collects multiple requests and executes them in a single batch.
    """

    def __init__(
        self,
        batch_func: Callable[[list[str]], Awaitable[dict[str, T]]],
        max_batch_size: int = 100,
        max_wait_ms: int = 50,
    ) -> None:
        """Initialize batch coalescer.

        Args:
            batch_func: Function to execute batch (keys -> results).
            max_batch_size: Maximum batch size.
            max_wait_ms: Maximum wait time before executing batch.
        """
        self._batch_func = batch_func
        self._max_batch_size = max_batch_size
        self._max_wait_ms = max_wait_ms
        self._pending: dict[str, asyncio.Future[T]] = {}
        self._batch_keys: list[str] = []
        self._lock = asyncio.Lock()
        self._batch_task: asyncio.Task | None = None

    async def get(self, key: str) -> T:
        """Get a value, batching with other concurrent requests.

        Args:
            key: Key to fetch.

        Returns:
            Value for the key.
        """
        async with self._lock:
            # Check if already pending
            if key in self._pending:
                return await self._pending[key]

            # Create future for this request
            future: asyncio.Future[T] = asyncio.get_event_loop().create_future()
            self._pending[key] = future
            self._batch_keys.append(key)

            # Start batch timer if needed
            if self._batch_task is None:
                self._batch_task = asyncio.create_task(self._execute_batch_after_delay())

            # Execute immediately if batch is full
            if len(self._batch_keys) >= self._max_batch_size:
                if self._batch_task:
                    self._batch_task.cancel()
                asyncio.create_task(self._execute_batch())

        return await future

    async def _execute_batch_after_delay(self) -> None:
        """Execute batch after delay."""
        await asyncio.sleep(self._max_wait_ms / 1000)
        await self._execute_batch()

    async def _execute_batch(self) -> None:
        """Execute the pending batch."""
        async with self._lock:
            if not self._batch_keys:
                return

            keys = self._batch_keys.copy()
            futures = {k: self._pending[k] for k in keys}

            self._batch_keys.clear()
            self._batch_task = None

        try:
            results = await self._batch_func(keys)

            for key, future in futures.items():
                if key in results and not future.done():
                    future.set_result(results[key])
                elif not future.done():
                    future.set_exception(KeyError(f"Key not found: {key}"))

        except Exception as e:
            for future in futures.values():
                if not future.done():
                    future.set_exception(e)

        finally:
            async with self._lock:
                for key in keys:
                    self._pending.pop(key, None)
