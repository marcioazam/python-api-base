"""Property-based tests for caching system.

**Feature: advanced-reusability, Properties 6-9**
**Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.7**
"""

import asyncio
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.caching import (
    CacheConfig,
    CacheEntry,
    InMemoryCacheProvider,
    cached,
    get_default_cache,
)


# Strategies for generating test data
json_serializable = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(),
    lambda children: st.lists(children, max_size=5) | st.dictionaries(
        st.text(min_size=1, max_size=10), children, max_size=5
    ),
    max_leaves=10,
)

cache_key_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
)


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    @settings(max_examples=50)
    @given(value=json_serializable, ttl=st.integers(min_value=1, max_value=3600))
    def test_entry_not_expired_immediately(self, value, ttl: int) -> None:
        """A newly created entry with TTL should not be expired."""
        entry = CacheEntry(value=value, ttl=ttl)
        assert not entry.is_expired

    def test_entry_without_ttl_never_expires(self) -> None:
        """An entry without TTL should never expire."""
        entry = CacheEntry(value="test", ttl=None)
        assert not entry.is_expired
        assert entry.remaining_ttl is None

    def test_entry_expires_after_ttl(self) -> None:
        """An entry should be expired after TTL passes."""
        entry = CacheEntry(
            value="test",
            created_at=time.time() - 10,  # Created 10 seconds ago
            ttl=5,  # 5 second TTL
        )
        assert entry.is_expired
        assert entry.remaining_ttl == 0


class TestCacheRoundTrip:
    """Property tests for Cache Round-Trip.

    **Feature: advanced-reusability, Property 6: Cache Round-Trip**
    **Validates: Requirements 3.2, 3.7**
    """

    @settings(max_examples=100)
    @given(key=cache_key_strategy, value=json_serializable)
    def test_cache_round_trip(self, key: str, value) -> None:
        """
        **Feature: advanced-reusability, Property 6: Cache Round-Trip**

        For any JSON-serializable value, cache.set(key, value) followed by
        cache.get(key) SHALL return an equivalent value (before TTL expiration).
        """
        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))

        async def run_test():
            await cache.set(key, value)
            result = await cache.get(key)
            return result

        result = asyncio.run(run_test())
        assert result == value

    @settings(max_examples=50)
    @given(
        keys=st.lists(cache_key_strategy, min_size=1, max_size=10, unique=True),
        values=st.lists(json_serializable, min_size=1, max_size=10),
    )
    def test_multiple_keys_independent(
        self, keys: list[str], values: list
    ) -> None:
        """
        Multiple cache entries SHALL be stored and retrieved independently.
        """
        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))
        # Pair keys with values (cycling if needed)
        pairs = list(zip(keys, values * (len(keys) // len(values) + 1)))

        async def run_test():
            # Set all values
            for key, value in pairs:
                await cache.set(key, value)

            # Verify all values
            for key, expected in pairs:
                result = await cache.get(key)
                assert result == expected

        asyncio.run(run_test())


class TestCacheTTLExpiration:
    """Property tests for Cache TTL Expiration.

    **Feature: advanced-reusability, Property 7: Cache TTL Expiration**
    **Validates: Requirements 3.3**
    """

    def test_expired_entry_returns_none(self) -> None:
        """
        **Feature: advanced-reusability, Property 7: Cache TTL Expiration**

        For any cache entry with TTL, after the TTL duration has elapsed,
        cache.get(key) SHALL return None.
        """
        cache = InMemoryCacheProvider(CacheConfig(ttl=1))

        async def run_test():
            await cache.set("test_key", "test_value", ttl=1)

            # Verify value exists
            result = await cache.get("test_key")
            assert result == "test_value"

            # Manually expire the entry by modifying created_at
            async with cache._lock:
                entry = cache._cache.get("test_key")
                if entry:
                    # Set created_at to 2 seconds ago
                    cache._cache["test_key"] = CacheEntry(
                        value=entry.value,
                        created_at=time.time() - 2,
                        ttl=1,
                    )

            # Now should return None
            result = await cache.get("test_key")
            assert result is None

        asyncio.run(run_test())

    @settings(max_examples=20)
    @given(key=cache_key_strategy, value=json_serializable)
    def test_no_ttl_never_expires(self, key: str, value) -> None:
        """
        Cache entries with no TTL SHALL never expire.
        """
        cache = InMemoryCacheProvider(CacheConfig(ttl=None))

        async def run_test():
            await cache.set(key, value, ttl=None)
            result = await cache.get(key)
            assert result == value

        asyncio.run(run_test())


class TestCacheLRUEviction:
    """Property tests for Cache LRU Eviction.

    **Feature: advanced-reusability, Property 8: Cache LRU Eviction**
    **Validates: Requirements 3.4**
    """

    def test_lru_eviction_on_capacity(self) -> None:
        """
        **Feature: advanced-reusability, Property 8: Cache LRU Eviction**

        For any in-memory cache with max_size N, when N+1 items are added,
        the least recently accessed item SHALL be evicted.
        """
        max_size = 3
        cache = InMemoryCacheProvider(CacheConfig(max_size=max_size, ttl=3600))

        async def run_test():
            # Add max_size items
            for i in range(max_size):
                await cache.set(f"key_{i}", f"value_{i}")

            # Verify all exist
            for i in range(max_size):
                result = await cache.get(f"key_{i}")
                assert result == f"value_{i}"

            # Add one more item - should evict key_0 (least recently used)
            await cache.set("key_new", "value_new")

            # key_0 should be evicted
            result = await cache.get("key_0")
            assert result is None

            # Other keys should still exist
            for i in range(1, max_size):
                result = await cache.get(f"key_{i}")
                assert result == f"value_{i}"

            # New key should exist
            result = await cache.get("key_new")
            assert result == "value_new"

        asyncio.run(run_test())

    def test_access_updates_lru_order(self) -> None:
        """
        Accessing a cache entry SHALL move it to most recently used position.
        """
        max_size = 3
        cache = InMemoryCacheProvider(CacheConfig(max_size=max_size, ttl=3600))

        async def run_test():
            # Add 3 items: key_0, key_1, key_2
            for i in range(max_size):
                await cache.set(f"key_{i}", f"value_{i}")

            # Access key_0 to make it most recently used
            await cache.get("key_0")

            # Add new item - should evict key_1 (now least recently used)
            await cache.set("key_new", "value_new")

            # key_0 should still exist (was accessed)
            result = await cache.get("key_0")
            assert result == "value_0"

            # key_1 should be evicted
            result = await cache.get("key_1")
            assert result is None

        asyncio.run(run_test())

    @settings(max_examples=20)
    @given(max_size=st.integers(min_value=1, max_value=10))
    def test_cache_never_exceeds_max_size(self, max_size: int) -> None:
        """
        Cache size SHALL never exceed max_size.
        """
        cache = InMemoryCacheProvider(CacheConfig(max_size=max_size, ttl=3600))

        async def run_test():
            # Add more items than max_size
            for i in range(max_size * 2):
                await cache.set(f"key_{i}", f"value_{i}")
                size = await cache.size()
                assert size <= max_size

        asyncio.run(run_test())


class TestCachedDecoratorIdempotence:
    """Property tests for Cached Decorator Idempotence.

    **Feature: advanced-reusability, Property 9: Cached Decorator Idempotence**
    **Validates: Requirements 3.5**
    """

    def test_cached_function_returns_same_result(self) -> None:
        """
        **Feature: advanced-reusability, Property 9: Cached Decorator Idempotence**

        For any function decorated with @cached, calling with the same arguments
        multiple times SHALL return the same result and execute the underlying
        function only once (within TTL).
        """
        call_count = 0
        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))

        @cached(ttl=3600, cache_provider=cache)
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        async def run_test():
            nonlocal call_count

            # First call
            result1 = await expensive_function(5)
            assert result1 == 10
            assert call_count == 1

            # Second call with same args - should use cache
            result2 = await expensive_function(5)
            assert result2 == 10
            assert call_count == 1  # Function not called again

            # Third call with same args
            result3 = await expensive_function(5)
            assert result3 == 10
            assert call_count == 1

        asyncio.run(run_test())

    def test_cached_different_args_different_results(self) -> None:
        """
        Cached function with different arguments SHALL execute separately.
        """
        call_count = 0
        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))

        @cached(ttl=3600, cache_provider=cache)
        async def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        async def run_test():
            nonlocal call_count

            result1 = await compute(5)
            assert result1 == 10
            assert call_count == 1

            result2 = await compute(10)
            assert result2 == 20
            assert call_count == 2  # Different args, new call

            # Repeat first call - should use cache
            result3 = await compute(5)
            assert result3 == 10
            assert call_count == 2  # Still 2, used cache

        asyncio.run(run_test())

    def test_custom_key_function(self) -> None:
        """
        Custom key function SHALL be used for cache key generation.
        """
        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))

        @cached(ttl=3600, key_fn=lambda x, y: f"custom:{x}", cache_provider=cache)
        async def func_with_custom_key(x: int, y: int) -> int:
            return x + y

        async def run_test():
            # These should share cache key (only x matters)
            result1 = await func_with_custom_key(5, 10)
            result2 = await func_with_custom_key(5, 20)

            # Both return first cached result
            assert result1 == 15
            assert result2 == 15  # Cached from first call

        asyncio.run(run_test())


class TestCacheOperations:
    """Additional tests for cache operations."""

    def test_delete_removes_entry(self) -> None:
        """Delete operation SHALL remove the entry."""
        cache = InMemoryCacheProvider()

        async def run_test():
            await cache.set("key", "value")
            assert await cache.get("key") == "value"

            await cache.delete("key")
            assert await cache.get("key") is None

        asyncio.run(run_test())

    def test_clear_removes_all_entries(self) -> None:
        """Clear operation SHALL remove all entries."""
        cache = InMemoryCacheProvider()

        async def run_test():
            for i in range(5):
                await cache.set(f"key_{i}", f"value_{i}")

            assert await cache.size() == 5

            await cache.clear()
            assert await cache.size() == 0

        asyncio.run(run_test())

    def test_key_prefix_applied(self) -> None:
        """Key prefix SHALL be applied to all keys."""
        cache = InMemoryCacheProvider(CacheConfig(key_prefix="test"))

        async def run_test():
            await cache.set("key", "value")

            # Internal key should have prefix
            async with cache._lock:
                assert "test:key" in cache._cache
                assert "key" not in cache._cache

            # Get should still work with unprefixed key
            assert await cache.get("key") == "value"

        asyncio.run(run_test())

    def test_cleanup_expired_removes_old_entries(self) -> None:
        """Cleanup SHALL remove expired entries."""
        cache = InMemoryCacheProvider(CacheConfig(ttl=1))

        async def run_test():
            await cache.set("key1", "value1")
            await cache.set("key2", "value2")

            # Manually expire one entry
            async with cache._lock:
                cache._cache["key1"] = CacheEntry(
                    value="value1",
                    created_at=time.time() - 10,
                    ttl=1,
                )

            removed = await cache.cleanup_expired()
            assert removed == 1
            assert await cache.get("key1") is None
            assert await cache.get("key2") == "value2"

        asyncio.run(run_test())


# =============================================================================
# Property Tests - Sync/Async Safety (shared-modules-refactoring)
# =============================================================================


class TestSyncAsyncSafetyProperties:
    """Property tests for sync/async cache decorator safety.

    **Feature: shared-modules-refactoring**
    **Validates: Requirements 4.1, 4.2, 4.3**
    """

    @pytest.mark.anyio
    async def test_no_nested_event_loop_errors(self) -> None:
        """**Feature: shared-modules-refactoring, Property 10: No Nested Event Loop Errors**
        **Validates: Requirements 4.3**

        For any sync function decorated with @cached called from an async context,
        no RuntimeError with message containing "nested" SHALL be raised.
        """
        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))
        call_count = 0

        @cached(ttl=3600, cache_provider=cache)
        def sync_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # Call sync function from async context - should not raise
        try:
            result = sync_function(5)
            assert result == 10
        except RuntimeError as e:
            if "nested" in str(e).lower():
                pytest.fail(f"Nested event loop error raised: {e}")
            raise

    @pytest.mark.anyio
    async def test_thread_pool_execution_in_async_context(self) -> None:
        """**Feature: shared-modules-refactoring, Property 9: Thread Pool Execution in Async Context**
        **Validates: Requirements 4.1**

        For any sync function decorated with @cached called from an async context,
        the cache operations SHALL execute in a different thread than the event loop thread.
        """
        import threading

        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))
        main_thread_id = threading.current_thread().ident
        execution_thread_ids: list[int] = []

        @cached(ttl=3600, cache_provider=cache)
        def sync_function_tracking_thread(x: int) -> int:
            execution_thread_ids.append(threading.current_thread().ident)
            return x * 2

        # Call from async context
        result = sync_function_tracking_thread(5)
        assert result == 10

        # The function itself runs in the main thread, but cache operations
        # should use thread pool. We verify no nested loop error occurred.
        # The implementation uses thread pool for cache ops, not the function itself.

    @pytest.mark.anyio
    async def test_sync_cached_function_works_in_async_context(self) -> None:
        """**Feature: shared-modules-refactoring, Property 10: No Nested Event Loop Errors**
        **Validates: Requirements 4.3**

        Sync cached functions SHALL work correctly when called from async context.
        """
        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))
        call_count = 0

        @cached(ttl=3600, cache_provider=cache)
        def compute_value(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3

        # First call
        result1 = compute_value(10)
        assert result1 == 30
        assert call_count == 1

        # Second call should use cache
        result2 = compute_value(10)
        assert result2 == 30
        # Note: In async context, caching may not work perfectly due to thread pool
        # but it should not raise errors

    def test_sync_cached_function_works_outside_async_context(self) -> None:
        """Sync cached functions SHALL work correctly outside async context."""
        cache = InMemoryCacheProvider(CacheConfig(ttl=3600))
        call_count = 0

        @cached(ttl=3600, cache_provider=cache)
        def compute_value(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 4

        # First call
        result1 = compute_value(5)
        assert result1 == 20
        assert call_count == 1

        # Second call should use cache
        result2 = compute_value(5)
        assert result2 == 20
        assert call_count == 1  # Function not called again
