"""Property-based tests for request coalescing.

**Feature: api-architecture-analysis, Task 12.2: Request Coalescing**
**Validates: Requirements 6.1**
"""

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.request_coalescing import (
    BatchCoalescer,
    CoalescingConfig,
    CoalescingStats,
    CoalescingStrategy,
    RequestCoalescer,
)


# =============================================================================
# Property Tests - Configuration
# =============================================================================

class TestCoalescingConfigProperties:
    """Property tests for coalescing configuration."""

    @given(
        window_ms=st.integers(min_value=1, max_value=1000),
        max_wait_ms=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=50)
    def test_config_preserves_values(self, window_ms: int, max_wait_ms: int) -> None:
        """**Property 1: Config preserves values**

        *For any* valid configuration values, they should be preserved.

        **Validates: Requirements 6.1**
        """
        config = CoalescingConfig(window_ms=window_ms, max_wait_ms=max_wait_ms)

        assert config.window_ms == window_ms
        assert config.max_wait_ms == max_wait_ms

    def test_config_defaults(self) -> None:
        """**Property 2: Config has sensible defaults**

        Default configuration should have reasonable values.

        **Validates: Requirements 6.1**
        """
        config = CoalescingConfig()

        assert config.strategy == CoalescingStrategy.FIRST_WINS
        assert config.window_ms == 100
        assert config.max_wait_ms == 5000
        assert config.max_coalesced == 100
        assert config.key_ttl_ms == 10000

    @given(strategy=st.sampled_from(list(CoalescingStrategy)))
    @settings(max_examples=10)
    def test_all_strategies_valid(self, strategy: CoalescingStrategy) -> None:
        """**Property 3: All strategies are valid**

        *For any* strategy, it should be usable in config.

        **Validates: Requirements 6.1**
        """
        config = CoalescingConfig(strategy=strategy)
        assert config.strategy == strategy


# =============================================================================
# Property Tests - Key Generation
# =============================================================================

class TestKeyGenerationProperties:
    """Property tests for key generation."""

    @given(
        arg1=st.text(min_size=1, max_size=100),
        arg2=st.integers(),
    )
    @settings(max_examples=100)
    def test_same_args_same_key(self, arg1: str, arg2: int) -> None:
        """**Property 4: Same arguments produce same key**

        *For any* arguments, calling generate_key twice should produce
        the same key.

        **Validates: Requirements 6.1**
        """
        key1 = RequestCoalescer.generate_key(arg1, arg2)
        key2 = RequestCoalescer.generate_key(arg1, arg2)

        assert key1 == key2

    @given(
        arg1=st.text(min_size=1, max_size=100),
        arg2=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_different_args_different_keys(self, arg1: str, arg2: str) -> None:
        """**Property 5: Different arguments produce different keys**

        *For any* different arguments, keys should be different.

        **Validates: Requirements 6.1**
        """
        if arg1 == arg2:
            return

        key1 = RequestCoalescer.generate_key(arg1)
        key2 = RequestCoalescer.generate_key(arg2)

        assert key1 != key2

    @given(
        args=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
        kwargs=st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
            st.integers(),
            min_size=0,
            max_size=3,
        ),
    )
    @settings(max_examples=100)
    def test_key_is_valid_string(self, args: list[str], kwargs: dict) -> None:
        """**Property 6: Generated key is valid string**

        *For any* arguments, key should be a non-empty hex string.

        **Validates: Requirements 6.1**
        """
        key = RequestCoalescer.generate_key(*args, **kwargs)

        assert isinstance(key, str)
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)


# =============================================================================
# Property Tests - Request Coalescing
# =============================================================================

class TestRequestCoalescerProperties:
    """Property tests for request coalescer."""

    async def test_single_request_executes(self) -> None:
        """**Property 7: Single request executes normally**

        A single request should execute and return result.

        **Validates: Requirements 6.1**
        """
        coalescer: RequestCoalescer[int] = RequestCoalescer()
        call_count = 0

        async def fetch() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        result = await coalescer.execute("key1", fetch)

        assert result == 42
        assert call_count == 1

    async def test_concurrent_requests_coalesced(self) -> None:
        """**Property 8: Concurrent requests are coalesced**

        Multiple concurrent requests with same key should be coalesced.

        **Validates: Requirements 6.1**
        """
        coalescer: RequestCoalescer[int] = RequestCoalescer()
        call_count = 0

        async def fetch() -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return 42

        # Start multiple concurrent requests
        tasks = [
            asyncio.create_task(coalescer.execute("key1", fetch))
            for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert all(r == 42 for r in results)
        assert call_count == 1  # Only one actual execution

    async def test_different_keys_not_coalesced(self) -> None:
        """**Property 9: Different keys are not coalesced**

        Requests with different keys should execute separately.

        **Validates: Requirements 6.1**
        """
        coalescer: RequestCoalescer[int] = RequestCoalescer()
        call_count = 0

        async def fetch() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = await coalescer.execute("key1", fetch)
        result2 = await coalescer.execute("key2", fetch)

        assert result1 == 1
        assert result2 == 2
        assert call_count == 2

    async def test_cache_hit(self) -> None:
        """**Property 10: Cached results are returned**

        Subsequent requests should return cached result.

        **Validates: Requirements 6.1**
        """
        coalescer: RequestCoalescer[int] = RequestCoalescer()
        call_count = 0

        async def fetch() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        result1 = await coalescer.execute("key1", fetch)
        result2 = await coalescer.execute("key1", fetch)

        assert result1 == 42
        assert result2 == 42
        assert call_count == 1  # Only one execution

        stats = coalescer.get_stats()
        assert stats.cache_hits == 1

    async def test_stats_tracking(self) -> None:
        """**Property 11: Statistics are tracked correctly**

        Coalescer should track request statistics.

        **Validates: Requirements 6.1**
        """
        coalescer: RequestCoalescer[int] = RequestCoalescer()

        async def fetch() -> int:
            return 42

        await coalescer.execute("key1", fetch)
        await coalescer.execute("key2", fetch)

        stats = coalescer.get_stats()

        assert stats.total_requests == 2
        assert stats.executed_requests == 2

    async def test_clear_cache(self) -> None:
        """**Property 12: Clear cache removes all entries**

        Clearing cache should remove all cached results.

        **Validates: Requirements 6.1**
        """
        coalescer: RequestCoalescer[int] = RequestCoalescer()

        async def fetch() -> int:
            return 42

        await coalescer.execute("key1", fetch)
        await coalescer.execute("key2", fetch)

        assert coalescer.cache_size == 2

        cleared = coalescer.clear_cache()

        assert cleared == 2
        assert coalescer.cache_size == 0

    async def test_execute_with_args(self) -> None:
        """**Property 13: Execute with args generates key automatically**

        execute_with_args should generate key from arguments.

        **Validates: Requirements 6.1**
        """
        coalescer: RequestCoalescer[int] = RequestCoalescer()
        call_count = 0

        async def fetch(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + y

        result1 = await coalescer.execute_with_args(fetch, 1, 2)
        result2 = await coalescer.execute_with_args(fetch, 1, 2)

        assert result1 == 3
        assert result2 == 3
        assert call_count == 1  # Cached


# =============================================================================
# Property Tests - Batch Coalescer
# =============================================================================

class TestBatchCoalescerProperties:
    """Property tests for batch coalescer."""

    async def test_single_get_works(self) -> None:
        """**Property 14: Single get works correctly**

        A single get should return the correct value.

        **Validates: Requirements 6.1**
        """
        async def batch_fetch(keys: list[str]) -> dict[str, int]:
            return {k: len(k) for k in keys}

        coalescer = BatchCoalescer(batch_fetch, max_wait_ms=10)

        result = await coalescer.get("hello")

        assert result == 5

    async def test_concurrent_gets_batched(self) -> None:
        """**Property 15: Concurrent gets are batched**

        Multiple concurrent gets should be batched together.

        **Validates: Requirements 6.1**
        """
        batch_calls = []

        async def batch_fetch(keys: list[str]) -> dict[str, int]:
            batch_calls.append(keys)
            return {k: len(k) for k in keys}

        coalescer = BatchCoalescer(batch_fetch, max_wait_ms=50)

        # Start concurrent requests
        tasks = [
            asyncio.create_task(coalescer.get("a")),
            asyncio.create_task(coalescer.get("bb")),
            asyncio.create_task(coalescer.get("ccc")),
        ]

        results = await asyncio.gather(*tasks)

        assert results == [1, 2, 3]
        # Should be batched into one call
        assert len(batch_calls) == 1
        assert set(batch_calls[0]) == {"a", "bb", "ccc"}

    @given(keys=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5, unique=True))
    @settings(max_examples=20)
    async def test_all_keys_resolved(self, keys: list[str]) -> None:
        """**Property 16: All keys are resolved**

        *For any* set of keys, all should be resolved correctly.

        **Validates: Requirements 6.1**
        """
        async def batch_fetch(batch_keys: list[str]) -> dict[str, int]:
            return {k: len(k) for k in batch_keys}

        coalescer = BatchCoalescer(batch_fetch, max_wait_ms=10)

        tasks = [asyncio.create_task(coalescer.get(k)) for k in keys]
        results = await asyncio.gather(*tasks)

        expected = [len(k) for k in keys]
        assert results == expected


# =============================================================================
# Property Tests - Coalescing Stats
# =============================================================================

class TestCoalescingStatsProperties:
    """Property tests for coalescing statistics."""

    def test_stats_initial_values(self) -> None:
        """**Property 17: Stats have zero initial values**

        Initial stats should all be zero.

        **Validates: Requirements 6.1**
        """
        stats = CoalescingStats()

        assert stats.total_requests == 0
        assert stats.coalesced_requests == 0
        assert stats.executed_requests == 0
        assert stats.cache_hits == 0
        assert stats.avg_coalesced_per_request == 0.0

    async def test_stats_updated_correctly(self) -> None:
        """**Property 18: Stats are updated correctly**

        After operations, stats should reflect actual counts.

        **Validates: Requirements 6.1**
        """
        coalescer: RequestCoalescer[int] = RequestCoalescer()

        async def fetch() -> int:
            await asyncio.sleep(0.05)
            return 42

        # Execute some requests
        await coalescer.execute("key1", fetch)
        await coalescer.execute("key1", fetch)  # Cache hit

        stats = coalescer.get_stats()

        assert stats.total_requests == 2
        assert stats.executed_requests == 1
        assert stats.cache_hits == 1
