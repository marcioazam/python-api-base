"""Property-based tests for connection pool.

**Feature: api-architecture-analysis, Task 12.1: Connection Pooling Manager**
**Validates: Requirements 6.1, 6.4**
"""

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.connection_pool import (
    AcquireTimeoutError,
    BaseConnectionFactory,
    ConnectionInfo,
    ConnectionPool,
    ConnectionState,
    PoolConfig,
    PoolStats,
)


# =============================================================================
# Test Connection Factory
# =============================================================================

class MockConnection:
    """Mock connection for testing."""

    def __init__(self, conn_id: int) -> None:
        self.conn_id = conn_id
        self.is_open = True

    def close(self) -> None:
        self.is_open = False


class MockConnectionFactory(BaseConnectionFactory[MockConnection]):
    """Mock connection factory for testing."""

    def __init__(self, fail_validation: bool = False) -> None:
        self._counter = 0
        self._fail_validation = fail_validation

    async def create(self) -> MockConnection:
        self._counter += 1
        return MockConnection(self._counter)

    async def destroy(self, connection: MockConnection) -> None:
        connection.close()

    async def validate(self, connection: MockConnection) -> bool:
        if self._fail_validation:
            return False
        return connection.is_open


# =============================================================================
# Property Tests - Pool Configuration
# =============================================================================

class TestPoolConfigProperties:
    """Property tests for pool configuration."""

    @given(
        min_size=st.integers(min_value=1, max_value=10),
        max_size=st.integers(min_value=10, max_value=100),
    )
    @settings(max_examples=50)
    def test_config_preserves_values(self, min_size: int, max_size: int) -> None:
        """**Property 1: Config preserves values**

        *For any* valid configuration values, they should be preserved.

        **Validates: Requirements 6.1, 6.4**
        """
        config = PoolConfig(min_size=min_size, max_size=max_size)

        assert config.min_size == min_size
        assert config.max_size == max_size

    def test_config_defaults(self) -> None:
        """**Property 2: Config has sensible defaults**

        Default configuration should have reasonable values.

        **Validates: Requirements 6.1, 6.4**
        """
        config = PoolConfig()

        assert config.min_size == 5
        assert config.max_size == 20
        assert config.max_idle_time == 300
        assert config.health_check_interval == 30
        assert config.acquire_timeout == 10.0
        assert config.max_lifetime == 3600
        assert config.retry_attempts == 3


# =============================================================================
# Property Tests - Connection Info
# =============================================================================

class TestConnectionInfoProperties:
    """Property tests for connection info."""

    @given(conn_id=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_connection_info_initial_state(self, conn_id: str) -> None:
        """**Property 3: Connection info has correct initial state**

        *For any* connection ID, initial state should be IDLE.

        **Validates: Requirements 6.1, 6.4**
        """
        info = ConnectionInfo(id=conn_id)

        assert info.id == conn_id
        assert info.state == ConnectionState.IDLE
        assert info.use_count == 0
        assert info.health_check_failures == 0

    @given(conn_id=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_connection_info_has_timestamps(self, conn_id: str) -> None:
        """**Property 4: Connection info has timestamps**

        *For any* connection info, timestamps should be set.

        **Validates: Requirements 6.1, 6.4**
        """
        info = ConnectionInfo(id=conn_id)

        assert info.created_at is not None
        assert info.last_used_at is not None


# =============================================================================
# Property Tests - Pool Stats
# =============================================================================

class TestPoolStatsProperties:
    """Property tests for pool statistics."""

    def test_stats_initial_values(self) -> None:
        """**Property 5: Stats have zero initial values**

        Initial pool stats should all be zero.

        **Validates: Requirements 6.1, 6.4**
        """
        stats = PoolStats()

        assert stats.total_connections == 0
        assert stats.idle_connections == 0
        assert stats.in_use_connections == 0
        assert stats.unhealthy_connections == 0
        assert stats.total_acquires == 0
        assert stats.total_releases == 0
        assert stats.total_timeouts == 0
        assert stats.avg_wait_time_ms == 0.0


# =============================================================================
# Property Tests - Connection Pool
# =============================================================================

class TestConnectionPoolProperties:
    """Property tests for connection pool."""

    @given(min_size=st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    async def test_pool_initializes_min_connections(self, min_size: int) -> None:
        """**Property 6: Pool initializes with min connections**

        *For any* min_size, pool should create that many connections on init.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=min_size, max_size=min_size + 10)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        try:
            stats = pool.get_stats()
            assert stats.total_connections == min_size
            assert stats.idle_connections == min_size
        finally:
            await pool.close()

    async def test_acquire_returns_connection(self) -> None:
        """**Property 7: Acquire returns valid connection**

        Acquiring from pool should return a valid connection.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        try:
            connection, conn_id = await pool.acquire()

            assert connection is not None
            assert isinstance(connection, MockConnection)
            assert conn_id is not None
        finally:
            await pool.release(conn_id)
            await pool.close()

    async def test_acquire_updates_stats(self) -> None:
        """**Property 8: Acquire updates statistics**

        Acquiring should update pool statistics correctly.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=2, max_size=5)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        try:
            _, conn_id = await pool.acquire()
            stats = pool.get_stats()

            assert stats.total_acquires == 1
            assert stats.in_use_connections == 1
            assert stats.idle_connections == 1  # 2 - 1
        finally:
            await pool.release(conn_id)
            await pool.close()

    async def test_release_returns_connection_to_pool(self) -> None:
        """**Property 9: Release returns connection to pool**

        Releasing should make connection available again.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        try:
            _, conn_id = await pool.acquire()
            await pool.release(conn_id)

            stats = pool.get_stats()
            assert stats.total_releases == 1
            assert stats.in_use_connections == 0
            assert stats.idle_connections == 1
        finally:
            await pool.close()

    @given(num_acquires=st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    async def test_multiple_acquires(self, num_acquires: int) -> None:
        """**Property 10: Multiple acquires work correctly**

        *For any* number of acquires within pool size, all should succeed.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=num_acquires, max_size=num_acquires + 5)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        conn_ids = []
        try:
            for _ in range(num_acquires):
                _, conn_id = await pool.acquire()
                conn_ids.append(conn_id)

            stats = pool.get_stats()
            assert stats.total_acquires == num_acquires
            assert stats.in_use_connections == num_acquires
        finally:
            for conn_id in conn_ids:
                await pool.release(conn_id)
            await pool.close()

    async def test_pool_close_releases_all(self) -> None:
        """**Property 11: Close releases all connections**

        Closing pool should release all connections.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=3, max_size=5)
        pool = ConnectionPool(factory, config)

        await pool.initialize()
        await pool.close()

        assert pool.is_closed
        assert pool.size == 0

    async def test_acquire_timeout(self) -> None:
        """**Property 12: Acquire times out when pool exhausted**

        When pool is exhausted and timeout expires, should raise error.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=1, max_size=1, acquire_timeout=0.1)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        try:
            # Acquire the only connection
            _, conn_id = await pool.acquire()

            # Try to acquire another (should timeout)
            try:
                await pool.acquire()
                assert False, "Should have raised AcquireTimeoutError"
            except AcquireTimeoutError as e:
                assert e.timeout == 0.1
        finally:
            await pool.release(conn_id)
            await pool.close()

    async def test_get_stats_returns_copy(self) -> None:
        """**Property 13: Get stats returns copy**

        Getting stats should return a copy, not the original.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        try:
            stats1 = pool.get_stats()
            stats2 = pool.get_stats()

            assert stats1 is not stats2
            assert stats1.total_connections == stats2.total_connections
        finally:
            await pool.close()


# =============================================================================
# Property Tests - Connection States
# =============================================================================

class TestConnectionStateProperties:
    """Property tests for connection states."""

    def test_all_states_defined(self) -> None:
        """**Property 14: All connection states are defined**

        All expected connection states should be available.

        **Validates: Requirements 6.1, 6.4**
        """
        assert ConnectionState.IDLE == "idle"
        assert ConnectionState.IN_USE == "in_use"
        assert ConnectionState.UNHEALTHY == "unhealthy"
        assert ConnectionState.CLOSED == "closed"

    async def test_state_transitions(self) -> None:
        """**Property 15: State transitions are correct**

        Connection states should transition correctly during lifecycle.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        try:
            # Initial state is IDLE
            conn_id = list(pool._connections.keys())[0]
            _, info = pool._connections[conn_id]
            assert info.state == ConnectionState.IDLE

            # After acquire, state is IN_USE
            _, acquired_id = await pool.acquire()
            _, info = pool._connections[acquired_id]
            assert info.state == ConnectionState.IN_USE

            # After release, state is IDLE
            await pool.release(acquired_id)
            _, info = pool._connections[acquired_id]
            assert info.state == ConnectionState.IDLE
        finally:
            await pool.close()


# =============================================================================
# Property Tests - Pool Size
# =============================================================================

class TestPoolSizeProperties:
    """Property tests for pool size management."""

    @given(
        min_size=st.integers(min_value=1, max_value=5),
        max_size=st.integers(min_value=6, max_value=10),
    )
    @settings(max_examples=20)
    async def test_pool_respects_size_limits(
        self,
        min_size: int,
        max_size: int,
    ) -> None:
        """**Property 16: Pool respects size limits**

        *For any* min/max size, pool should stay within limits.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=min_size, max_size=max_size)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        try:
            assert pool.size >= min_size
            assert pool.size <= max_size
        finally:
            await pool.close()

    async def test_pool_grows_on_demand(self) -> None:
        """**Property 17: Pool grows on demand**

        Pool should create new connections when needed up to max.

        **Validates: Requirements 6.1, 6.4**
        """
        factory = MockConnectionFactory()
        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(factory, config)

        await pool.initialize()

        conn_ids = []
        try:
            # Acquire more than min_size
            for _ in range(3):
                _, conn_id = await pool.acquire()
                conn_ids.append(conn_id)

            assert pool.size >= 3
        finally:
            for conn_id in conn_ids:
                await pool.release(conn_id)
            await pool.close()
