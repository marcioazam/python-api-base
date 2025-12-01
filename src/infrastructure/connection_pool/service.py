"""Connection pool service implementation.

**Feature: full-codebase-review-2025, Task 1.1: Refactor connection_pool**
**Validates: Requirements 9.2**
"""

import asyncio
from datetime import datetime, UTC
from typing import Any

from .config import PoolConfig
from .enums import ConnectionState
from .errors import AcquireTimeoutError, PoolError
from .factory import ConnectionFactory
from .models import ConnectionInfo
from .stats import PoolStats


class ConnectionPool[T]:
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
        self._health_check_task: asyncio.Task[None] | None = None
        self._closed = False
        self._wait_times: list[float] = []
        self._counter = 0

    async def initialize(self) -> None:
        """Initialize pool with minimum connections."""
        async with self._lock:
            for _ in range(self._config.min_size):
                await self._create_connection()
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _create_connection(self) -> str:
        """Create a new connection and add to pool."""
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
        """
        if self._closed:
            raise PoolError("Pool is closed")

        start_time = asyncio.get_event_loop().time()
        try:
            conn_id = await asyncio.wait_for(
                self._get_idle_connection(),
                timeout=self._config.acquire_timeout,
            )
            connection, info = self._connections[conn_id]
            info.state = ConnectionState.IN_USE
            info.last_used_at = datetime.now(UTC)
            info.use_count += 1
            self._stats.idle_connections -= 1
            self._stats.in_use_connections += 1
            self._stats.total_acquires += 1
            self._update_wait_time(start_time)
            return connection, conn_id
        except asyncio.TimeoutError:
            self._stats.total_timeouts += 1
            raise AcquireTimeoutError(self._config.acquire_timeout)

    def _update_wait_time(self, start_time: float) -> None:
        """Update average wait time statistics."""
        wait_time = (asyncio.get_event_loop().time() - start_time) * 1000
        self._wait_times.append(wait_time)
        if len(self._wait_times) > 100:
            self._wait_times.pop(0)
        self._stats.avg_wait_time_ms = sum(self._wait_times) / len(self._wait_times)

    async def _get_idle_connection(self) -> str:
        """Get an idle connection, creating if needed."""
        while True:
            if not self._idle_queue.empty():
                conn_id = await self._idle_queue.get()
                if conn_id in self._connections:
                    _, info = self._connections[conn_id]
                    if info.state == ConnectionState.IDLE:
                        return conn_id
            async with self._lock:
                if self._stats.total_connections < self._config.max_size:
                    conn_id = await self._create_connection()
                    await self._idle_queue.get()
                    return conn_id
            await asyncio.sleep(0.1)

    async def release(self, conn_id: str) -> None:
        """Release a connection back to the pool."""
        if conn_id not in self._connections:
            return
        connection, info = self._connections[conn_id]
        age = (datetime.now(UTC) - info.created_at).total_seconds()
        if age > self._config.max_lifetime:
            await self._remove_connection(conn_id)
            return
        info.state = ConnectionState.IDLE
        info.last_used_at = datetime.now(UTC)
        self._stats.in_use_connections -= 1
        self._stats.idle_connections += 1
        self._stats.total_releases += 1
        await self._idle_queue.put(conn_id)

    async def _transition_state(
        self,
        conn_id: str,
        from_state: ConnectionState,
        to_state: ConnectionState,
    ) -> bool:
        """Atomically transition connection state and update counters.

        **Feature: shared-modules-phase2, Property 4**
        **Validates: Requirements 2.2**
        """
        async with self._lock:
            if conn_id not in self._connections:
                return False
            _, info = self._connections[conn_id]
            if info.state != from_state:
                return False
            self._decrement_state_counter(from_state)
            self._increment_state_counter(to_state)
            info.state = to_state
            return True

    def _decrement_state_counter(self, state: ConnectionState) -> None:
        """Decrement counter for given state."""
        if state == ConnectionState.IDLE:
            self._stats.idle_connections -= 1
        elif state == ConnectionState.IN_USE:
            self._stats.in_use_connections -= 1
        elif state == ConnectionState.UNHEALTHY:
            self._stats.unhealthy_connections -= 1

    def _increment_state_counter(self, state: ConnectionState) -> None:
        """Increment counter for given state."""
        if state == ConnectionState.IDLE:
            self._stats.idle_connections += 1
        elif state == ConnectionState.IN_USE:
            self._stats.in_use_connections += 1
        elif state == ConnectionState.UNHEALTHY:
            self._stats.unhealthy_connections += 1

    async def _remove_connection(self, conn_id: str) -> None:
        """Remove a connection from the pool."""
        if conn_id not in self._connections:
            return
        connection, info = self._connections.pop(conn_id)
        try:
            await self._factory.destroy(connection)
        except Exception:
            pass
        self._decrement_state_counter(info.state)
        self._stats.total_connections -= 1

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while not self._closed:
            await asyncio.sleep(self._config.health_check_interval)
            await self._run_health_checks()

    async def _run_health_checks(self) -> None:
        """Run health checks on idle connections."""
        for conn_id in list(self._connections.keys()):
            if conn_id not in self._connections:
                continue
            connection, info = self._connections[conn_id]
            if info.state != ConnectionState.IDLE:
                continue
            await self._check_connection_health(conn_id, connection, info)
        await self._ensure_minimum_connections()

    async def _check_connection_health(
        self, conn_id: str, connection: T, info: ConnectionInfo
    ) -> None:
        """Check health of a single connection."""
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

    async def _ensure_minimum_connections(self) -> None:
        """Ensure pool has minimum connections."""
        async with self._lock:
            while self._stats.total_connections < self._config.min_size:
                await self._create_connection()

    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        return self._stats.model_copy()

    async def close(self) -> None:
        """Close the pool and all connections.

        **Feature: shared-modules-phase2, Property 3**
        **Validates: Requirements 1.2**
        """
        self._closed = True
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        tasks = [
            asyncio.create_task(self._remove_connection(cid))
            for cid in list(self._connections.keys())
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._closed

    @property
    def size(self) -> int:
        """Get current pool size."""
        return self._stats.total_connections


class ConnectionPoolContext[T]:
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
