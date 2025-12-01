"""Property-based tests for caching layer.

**Feature: enterprise-features-2025, Tasks 1.2-1.7**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_app.shared.caching.providers import (
    CacheEntry,
    CacheStats,
    InMemoryCacheProvider,
)
from my_app.shared.caching.config import CacheConfig
from my_app.shared.caching.decorators import cached


# Strategies for generating test data
cache_keys = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
    min_size=1,
    max_size=20,
)
cache_values = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=100),
    st.lists(st.integers(), max_size=10),
    st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
)
ttl_values = st.integers(min_value=1, max_value=3600)


class TestCacheEntryProperties:
    """Property tests for CacheEntry dataclass."""

    @given(key=cache_keys, value=st.integers(), ttl=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_cache_entry_is_frozen(self, key: str, value: int, ttl: int) -> None:
        """**Property: CacheEntry is immutable (frozen=True)**"""
        now = datetime.now()
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            ttl=ttl,
            expires_at=now + timedelta(seconds=ttl),
        )
        with pytest.raises(AttributeError):
            entry.key = "new_key"  # type: ignore

    @given(key=cache_keys, value=cache_values)
    @settings(max_examples=100)
    def test_cache_entry_no_ttl_never_expires(self, key: str, value) -> None:
        """**Property: CacheEntry without TTL never expires**"""
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            ttl=None,
            expires_at=None,
        )
        assert not entry.is_expired


class TestCacheTTLExpiration:
    """**Feature: enterprise-features-2025, Property 1: Cache TTL Expiration**
    **Validates: Requirements 1.1, 1.2**
    """

    @given(key=cache_keys, value=cache_values)
    @settings(max_examples=50)
    def test_expired_entry_returns_none(self, key: str, value) -> None:
        """For any cache entry with expired TTL, retrieval returns None."""

        async def run_test() -> None:
            provider: InMemoryCacheProvider[object] = InMemoryCacheProvider(
                CacheConfig(ttl=1, max_size=100)
            )
            # Create entry that's already expired
            past = datetime.now() - timedelta(seconds=10)
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=past,
                ttl=1,
                expires_at=past + timedelta(seconds=1),
            )
            # Manually insert expired entry
            provider._cache[key] = entry

            # Retrieval should return None for expired entry
            result = await provider.get(key)
            assert result is None

        asyncio.run(run_test())


class TestCacheRoundTrip:
    """**Feature: enterprise-features-2025, Property 2: Cache Round-Trip Consistency**
    **Validates: Requirements 1.1, 1.2**
    """

    @given(key=cache_keys, value=st.integers())
    @settings(max_examples=100)
    def test_set_then_get_returns_same_value(self, key: str, value: int) -> None:
        """For any value stored in cache, retrieval returns equivalent value."""

        async def run_test() -> None:
            provider: InMemoryCacheProvider[int] = InMemoryCacheProvider(
                CacheConfig(ttl=3600, max_size=100)
            )
            await provider.set(key, value)
            result = await provider.get(key)
            assert result == value

        asyncio.run(run_test())

    @given(key=cache_keys, value=st.text(min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_string_round_trip(self, key: str, value: str) -> None:
        """String values round-trip correctly."""

        async def run_test() -> None:
            provider: InMemoryCacheProvider[str] = InMemoryCacheProvider()
            await provider.set(key, value)
            result = await provider.get(key)
            assert result == value

        asyncio.run(run_test())

    @given(key=cache_keys, value=st.lists(st.integers(), max_size=20))
    @settings(max_examples=50)
    def test_list_round_trip(self, key: str, value: list[int]) -> None:
        """List values round-trip correctly."""

        async def run_test() -> None:
            provider: InMemoryCacheProvider[list[int]] = InMemoryCacheProvider()
            await provider.set(key, value)
            result = await provider.get(key)
            assert result == value

        asyncio.run(run_test())


class TestCacheInvalidation:
    """**Feature: enterprise-features-2025, Property 3: Cache Invalidation Completeness**
    **Validates: Requirements 1.3**
    """

    @given(key=cache_keys, value=cache_values)
    @settings(max_examples=100)
    def test_delete_removes_key(self, key: str, value) -> None:
        """For any deleted key, subsequent retrieval returns None."""

        async def run_test() -> None:
            provider: InMemoryCacheProvider[object] = InMemoryCacheProvider()
            await provider.set(key, value)
            assert await provider.exists(key)

            deleted = await provider.delete(key)
            assert deleted is True

            result = await provider.get(key)
            assert result is None
            assert not await provider.exists(key)

        asyncio.run(run_test())

    @given(key=cache_keys)
    @settings(max_examples=50)
    def test_delete_nonexistent_returns_false(self, key: str) -> None:
        """Deleting non-existent key returns False."""

        async def run_test() -> None:
            provider: InMemoryCacheProvider[object] = InMemoryCacheProvider()
            deleted = await provider.delete(key)
            assert deleted is False

        asyncio.run(run_test())

    @given(
        keys=st.lists(cache_keys, min_size=1, max_size=10, unique=True),
        value=st.integers(),
    )
    @settings(max_examples=50)
    def test_clear_pattern_removes_matching_keys(
        self, keys: list[str], value: int
    ) -> None:
        """Clear pattern removes all matching keys."""

        async def run_test() -> None:
            provider: InMemoryCacheProvider[int] = InMemoryCacheProvider()
            for key in keys:
                await provider.set(key, value)

            # Clear all keys with wildcard pattern
            deleted = await provider.clear_pattern("*")
            assert deleted == len(keys)

            # Verify all keys are gone
            for key in keys:
                assert not await provider.exists(key)

        asyncio.run(run_test())


class TestCachedDecorator:
    """**Feature: enterprise-features-2025, Property 4: Cached Decorator Idempotence**
    **Validates: Requirements 1.4**
    """

    @given(x=st.integers(min_value=0, max_value=1000))
    @settings(max_examples=50)
    def test_cached_function_returns_same_result(self, x: int) -> None:
        """Calling cached function multiple times returns same result."""
        call_count = 0

        @cached(ttl=3600)
        async def expensive_computation(n: int) -> int:
            nonlocal call_count
            call_count += 1
            return n * 2

        async def run_test() -> None:
            nonlocal call_count
            call_count = 0

            result1 = await expensive_computation(x)
            result2 = await expensive_computation(x)
            result3 = await expensive_computation(x)

            assert result1 == result2 == result3 == x * 2
            # Function should only be called once due to caching
            assert call_count == 1

        asyncio.run(run_test())

    @given(x=st.integers(min_value=0, max_value=100), y=st.integers(min_value=101, max_value=200))
    @settings(max_examples=30)
    def test_different_args_different_cache_entries(self, x: int, y: int) -> None:
        """Different arguments create different cache entries."""
        # x and y are guaranteed different by strategy ranges

        async def run_test() -> None:
            provider: InMemoryCacheProvider[int] = InMemoryCacheProvider()

            # Set different values for different keys
            await provider.set(f"key_{x}", x * 3)
            await provider.set(f"key_{y}", y * 3)

            # Retrieve and verify
            result_x = await provider.get(f"key_{x}")
            result_y = await provider.get(f"key_{y}")

            assert result_x == x * 3
            assert result_y == y * 3
            assert result_x != result_y

        asyncio.run(run_test())


class TestCacheStats:
    """Tests for cache statistics."""

    @given(
        keys=st.lists(cache_keys, min_size=1, max_size=20, unique=True),
        value=st.integers(),
    )
    @settings(max_examples=30)
    def test_stats_track_hits_and_misses(
        self, keys: list[str], value: int
    ) -> None:
        """Cache stats accurately track hits and misses."""

        async def run_test() -> None:
            provider: InMemoryCacheProvider[int] = InMemoryCacheProvider()

            # Set all keys
            for key in keys:
                await provider.set(key, value)

            # Get all keys (hits)
            for key in keys:
                await provider.get(key)

            # Get non-existent keys (misses)
            for i in range(5):
                await provider.get(f"nonexistent_{i}")

            stats = await provider.get_stats()
            assert stats.hits == len(keys)
            assert stats.misses == 5
            assert stats.entry_count == len(keys)

        asyncio.run(run_test())
