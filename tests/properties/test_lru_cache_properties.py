"""Property-based tests for LRU Cache Eviction Behavior.

**Feature: architecture-restructuring-2025, Property 8: LRU Cache Eviction Behavior**
**Validates: Requirements 7.1**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

try:
    from infrastructure.cache.local_cache import LRUCache
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


key_strategy = st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")
value_strategy = st.one_of(st.integers(), st.text(max_size=100), st.booleans())


class TestLRUCacheEviction:
    """Property tests for LRU cache eviction behavior."""

    @settings(max_examples=100)
    @given(
        max_size=st.integers(min_value=1, max_value=10),
        keys=st.lists(key_strategy, min_size=2, max_size=20, unique=True),
    )
    def test_lru_evicts_oldest_when_full(self, max_size: int, keys: list[str]) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 8: LRU Cache Eviction Behavior**
        
        For any LRU cache with max_size N, when N+1 items are inserted,
        the least recently used item SHALL be evicted.
        **Validates: Requirements 7.1**
        """
        assume(len(keys) > max_size)
        
        cache = LRUCache(max_size=max_size)
        
        # Insert max_size items
        for i, key in enumerate(keys[:max_size]):
            cache.set(key, f"value_{i}")
        
        assert cache.size() == max_size
        
        # Insert one more item
        extra_key = keys[max_size]
        cache.set(extra_key, "extra_value")
        
        # Size should still be max_size
        assert cache.size() == max_size
        
        # First key should be evicted (LRU)
        assert cache.get(keys[0]) is None
        
        # New key should exist
        assert cache.get(extra_key) == "extra_value"

    @settings(max_examples=100)
    @given(
        max_size=st.integers(min_value=2, max_value=10),
        keys=st.lists(key_strategy, min_size=3, max_size=15, unique=True),
    )
    def test_access_updates_lru_order(self, max_size: int, keys: list[str]) -> None:
        """
        For any LRU cache, accessing an item SHALL move it to most recently used.
        **Validates: Requirements 7.1**
        """
        assume(len(keys) > max_size)
        
        cache = LRUCache(max_size=max_size)
        
        # Insert max_size items
        for i, key in enumerate(keys[:max_size]):
            cache.set(key, f"value_{i}")
        
        # Access the first key (making it most recently used)
        first_key = keys[0]
        cache.get(first_key)
        
        # Insert more items to trigger eviction
        for key in keys[max_size:max_size + max_size]:
            cache.set(key, "new_value")
        
        # First key should still exist (was accessed, so not LRU)
        # Only if we haven't inserted too many new items
        if len(keys[max_size:max_size + max_size]) < max_size:
            assert cache.get(first_key) is not None

    @settings(max_examples=100)
    @given(
        max_size=st.integers(min_value=1, max_value=20),
        num_items=st.integers(min_value=1, max_value=50),
    )
    def test_cache_never_exceeds_max_size(self, max_size: int, num_items: int) -> None:
        """
        For any sequence of insertions, cache size SHALL never exceed max_size.
        **Validates: Requirements 7.1**
        """
        cache = LRUCache(max_size=max_size)
        
        for i in range(num_items):
            cache.set(f"key_{i}", f"value_{i}")
            assert cache.size() <= max_size

    @settings(max_examples=50)
    @given(key=key_strategy, value=value_strategy)
    def test_get_set_roundtrip(self, key: str, value) -> None:
        """
        For any key-value pair, set then get SHALL return the same value.
        **Validates: Requirements 7.1**
        """
        cache = LRUCache(max_size=100)
        cache.set(key, value)
        assert cache.get(key) == value

    @settings(max_examples=50)
    @given(key=key_strategy)
    def test_delete_removes_item(self, key: str) -> None:
        """
        For any key, delete SHALL remove the item from cache.
        **Validates: Requirements 7.1**
        """
        cache = LRUCache(max_size=100)
        cache.set(key, "value")
        assert cache.get(key) is not None
        
        cache.delete(key)
        assert cache.get(key) is None
