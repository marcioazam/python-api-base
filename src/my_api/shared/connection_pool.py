"""Generic connection pooling with health checking and auto-recovery.

**Feature: api-architecture-analysis, Task 12.1: Connection Pooling Manager**
**Validates: Requirements 6.1, 6.4**

Provides type-safe connection pooling for database, HTTP, and other connections.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel


T = TypeVar("T")


class ConnectionState(str, Enum):
    """Connection state."""

    IDLE = "idle"
    IN_USE = "in_use"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class PoolConfig:
    """Connection pool configuration.

    Attributes:
        min_size: Minimum pool size.
        max_size: Maximum pool size.
        max_idle_time: Max time connection can be idle (seconds).
        health_check_interval: Interval between health checks (seconds).
        acquire_timeout: Timeout for acquiring connection (seconds).
        max_lifetime: Maximum connection lifetime (seconds).
        retry_attempts: Number of retry attempts for failed connections.
    """

    min_size: int = 5
    max_size: int = 20
    max_idle_time: int = 300
    health_check_interval: int = 30
    acquire_timeout: float = 10.0
    max_lifetime: int = 3600
    retry_attempts: int = 3


@dataclass
class ConnectionInfo:
    """Information about a pooled connection.

    Attributes:
        id: Unique connection identifier.
        state: Current connection state.
        created_at: Connection creation time.
        last_used_at: Last time connection was used.
        use_count: Number of times connection was used.
        health_check_failures: Consecutive health check failures.
    """

    id: str
    state: ConnectionState = ConnectionState.IDLE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0
    health_check_failures: int = 0


class PoolStats(BaseModel):
    """Pool statistics.

    Attributes:
        total_connections: Total connections in pool.
        idle_connections: Number of idle connections.
        in_use_connections: Number of connections in use.
        unhealthy_connections: Number of unhealthy connections.
        total_acquires: Total number of acquires.
        total_releases: Total number of releases.
        total_timeouts: Total number of acquire timeouts.
        avg_wait_time_ms: Average wait time in milliseconds.
    """

    total_connections: int = 0
    idle_connections: int = 0
    in_use_connections: int = 0
    unhealthy_connections: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    avg_wait_time_ms: float = 0.0


class PoolError(Exception):
    """Base pool error."""

    def __init__(self, message: str, error_code: str = "POOL_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class PoolExhaustedError(PoolError):
    """Pool exhausted error."""

    def __init__(self) -> None:
        super().__init__("Connection pool exhausted", "POOL_EXHAUSTED")


class AcquireTimeoutError(PoolError):
    """Acquire timeout error."""

    def __init__(self, timeout: float) -> None:
        super().__init__(f"Acquire timeout after {timeout}s", "ACQUIRE_TIMEOUT")
        self.timeout = timeout


class ConnectionError(PoolError):
    """Connection error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "CONNECTION_ERROR")


@runtime_checkable
class ConnectionFactory(Protocol[T]):
    """Protocol for connection factories."""

    async def create(self) -> T:
        """Create a new connection."""
        ...

    async def destroy(self, connection: T) -> None:
        """Destroy a connection."""
        ...

    async def validate(self, connection: T) -> bool:
        """Validate connection health."""
        ...


class BaseConnectionFactory(ABC, Generic[T]):
    """Base class for connection factories."""

    @abstractmethod
    async def create(self) -> T:
        """Create a new connection."""
        ...

    @abstractmethod
    async def destroy(self, connection: T) -> None:
        """Destroy a connection."""
        ...

    @abstractmethod
    async def validate(self, connection: T) -> bool:
        """Validate connection health."""
        ...


class ConnectionPool(Generic[T]):
    """Generic connection pool with health checking.

    Provides connection pooling with:
    - Configurable pool size
    - Health checking
    - Auto-recovery
    - Connection lifetime management
    - Statistics tracking
    """

    def __init__(
        self,
        factory: ConnectionFactory[T],
        config: PoolConfig | None = None,
    ) -> None:
        """Initialize connection pool.

        Args:
            factory: Connection factory.
            config: Pool configuration.
        """
        self._factory = factory
        self._config = config or PoolConfig()
        self._connections: dict[str, tuple[T, ConnectionInfo]] = {}
        self._idle_queue: asyncio.Queue[str] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._stats = PoolStats()
        self._health_check_task: asyncio.Task | None = None
        self._closed = False
        self._wait_times: list[float] = []
        self._counter = 0

    async def initialize(self) -> None:
        """Initialize pool with minimum connections."""
        async with self._lock:
            for _ in range(self._config.min_size):
                await self._create_connection()

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _create_connection(self) -> str:
        """Create a new connection and add to pool.

        Returns:
            Connection ID.
        """
        self._counter += 1
        conn_id = f"conn_{self._counter}"

        connection = await self._factory.create()
        info = ConnectionInfo(id=conn_id)

        self._connections[conn_id] = (connection, info)
        await self._idle_queue.put(conn_id)

        self._stats.total_connections += 1
        self._stats.idle_connections += 1

        return conn_id

    async def acquire(self) -> tuple[T, str]:
        """Acquire a connection from the pool.

        Returns:
            Tuple of (connection, connection_id).

        Raises:
            AcquireTimeoutError: If acquire times out.
            PoolExhaustedError: If pool is exhausted.
        """
        if self._closed:
            raise PoolError("Pool is closed")

        start_time = asyncio.get_event_loop().time()

        try:
            # Try to get from idle queue
            conn_id = await asyncio.wait_for(
                self._get_idle_connection(),
                timeout=self._config.acquire_timeout,
            )

            connection, info = self._connections[conn_id]
            info.state = ConnectionState.IN_USE
            info.last_used_at = datetime.now(timezone.utc)
            info.use_count += 1

            self._stats.idle_connections -= 1
            self._stats.in_use_connections += 1
            self._stats.total_acquires += 1

            # Track wait time
            wait_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self._wait_times.append(wait_time)
            if len(self._wait_times) > 100:
                self._wait_times.pop(0)
            self._stats.avg_wait_time_ms = sum(self._wait_times) / len(self._wait_times)

            return connection, conn_id

        except asyncio.TimeoutError:
            self._stats.total_timeouts += 1
            raise AcquireTimeoutError(self._config.acquire_timeout)

    async def _get_idle_connection(self) -> str:
        """Get an idle connection, creating if needed.

        Returns:
            Connection ID.
        """
        while True:
            # Try to get from queue
            if not self._idle_queue.empty():
                conn_id = await self._idle_queue.get()

                # Check if connection is still valid
                if conn_id in self._connections:
                    _, info = self._connections[conn_id]
                    if info.state == ConnectionState.IDLE:
                        return conn_id

            # Create new connection if under max
            async with self._lock:
                if self._stats.total_connections < self._config.max_size:
                    conn_id = await self._create_connection()
                    await self._idle_queue.get()  # Remove from queue
                    return conn_id

            # Wait for a connection to be released
            await asyncio.sleep(0.1)

    async def release(self, conn_id: str) -> None:
        """Release a connection back to the pool.

        Args:
            conn_id: Connection ID to release.
        """
        if conn_id not in self._connections:
            return

        connection, info = self._connections[conn_id]

        # Check if connection should be retired
        age = (datetime.now(timezone.utc) - info.created_at).total_seconds()
        if age > self._config.max_lifetime:
            await self._remove_connection(conn_id)
            return

        info.state = ConnectionState.IDLE
        info.last_used_at = datetime.now(timezone.utc)

        self._stats.in_use_connections -= 1
        self._stats.idle_connections += 1
        self._stats.total_releases += 1

        await self._idle_queue.put(conn_id)

    async def _remove_connection(self, conn_id: str) -> None:
        """Remove a connection from the pool.

        Args:
            conn_id: Connection ID to remove.
        """
        if conn_id not in self._connections:
            return

        connection, info = self._connections.pop(conn_id)

        try:
            await self._factory.destroy(connection)
        except Exception:
            pass

        if info.state == ConnectionState.IDLE:
            self._stats.idle_connections -= 1
        elif info.state == ConnectionState.IN_USE:
            self._stats.in_use_connections -= 1
        elif info.state == ConnectionState.UNHEALTHY:
            self._stats.unhealthy_connections -= 1

        self._stats.total_connections -= 1

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while not self._closed:
            await asyncio.sleep(self._config.health_check_interval)
            await self._run_health_checks()

    async def _run_health_checks(self) -> None:
        """Run health checks on idle connections."""
        conn_ids = list(self._connections.keys())

        for conn_id in conn_ids:
            if conn_id not in self._connections:
                continue

            connection, info = self._connections[conn_id]

            if info.state != ConnectionState.IDLE:
                continue

            try:
                is_healthy = await self._factory.validate(connection)

                if is_healthy:
                    info.health_check_failures = 0
                else:
                    info.health_check_failures += 1

                if info.health_check_failures >= self._config.retry_attempts:
                    info.state = ConnectionState.UNHEALTHY
                    self._stats.idle_connections -= 1
                    self._stats.unhealthy_connections += 1
                    await self._remove_connection(conn_id)

            except Exception:
                info.health_check_failures += 1

        # Ensure minimum connections
        async with self._lock:
            while self._stats.total_connections < self._config.min_size:
                await self._create_connection()

    def get_stats(self) -> PoolStats:
        """Get pool statistics.

        Returns:
            Current pool statistics.
        """
        return self._stats.model_copy()

    async def close(self) -> None:
        """Close the pool and all connections."""
        self._closed = True

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        conn_ids = list(self._connections.keys())
        for conn_id in conn_ids:
            await self._remove_connection(conn_id)

    @property
    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._closed

    @property
    def size(self) -> int:
        """Get current pool size."""
        return self._stats.total_connections


class ConnectionPoolContext(Generic[T]):
    """Context manager for connection pool."""

    def __init__(self, pool: ConnectionPool[T]) -> None:
        self._pool = pool
        self._connection: T | None = None
        self._conn_id: str | None = None

    async def __aenter__(self) -> T:
        self._connection, self._conn_id = await self._pool.acquire()
        return self._connection

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._conn_id:
            await self._pool.release(self._conn_id)
