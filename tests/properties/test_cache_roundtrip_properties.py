"""Property-based tests for Cache Get/Set Round-Trip.

**Feature: architecture-restructuring-2025, Property 9: Cache Get/Set Round-Trip**
**Validates: Requirements 7.2**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

try:
    from infrastructure.cache.local_cache import LRUCache
    from infrastructure.cache.providers import InMemoryCacheProvider
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


key_strategy = st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
string_value_strategy = st.text(max_size=200)
int_value_strategy = st.integers(min_value=-1000000, max_value=1000000)
float_value_strategy = st.floats(allow_nan=False, allow_infinity=False)
bool_value_strategy = st.booleans()
list_value_strategy = st.lists(st.integers(), max_size=20)
dict_value_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.one_of(st.integers(), st.text(max_size=50)),
    max_size=10,
)

serializable_value_strategy = st.one_of(
    string_value_strategy,
    int_value_strategy,
    float_value_strategy,
    bool_value_strategy,
    list_value_strategy,
    dict_value_strategy,
)


class TestCacheRoundTrip:
    """Property tests for cache get/set round-trip."""

    @settings(max_examples=100)
    @given(key=key_strategy, value=string_value_strategy)
    def test_string_roundtrip(self, key: str, value: str) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 9: Cache Get/Set Round-Trip**
        
        For any string value stored in cache, retrieving SHALL return equal value.
        **Validates: Requirements 7.2**
        """
        cache = LRUCache(max_size=1000)
        cache.set(key, value)
        assert cache.get(key) == value

    @settings(max_examples=100)
    @given(key=key_strategy, value=int_value_strategy)
    def test_integer_roundtrip(self, key: str, value: int) -> None:
        """
        For any integer value stored in cache, retrieving SHALL return equal value.
        **Validates: Requirements 7.2**
        """
        cache = LRUCache(max_size=1000)
        cache.set(key, value)
        assert cache.get(key) == value

    @settings(max_examples=100)
    @given(key=key_strategy, value=float_value_strategy)
    def test_float_roundtrip(self, key: str, value: float) -> None:
        """
        For any float value stored in cache, retrieving SHALL return equal value.
        **Validates: Requirements 7.2**
        """
        cache = LRUCache(max_size=1000)
        cache.set(key, value)
        assert cache.get(key) == value

    @settings(max_examples=100)
    @given(key=key_strategy, value=list_value_strategy)
    def test_list_roundtrip(self, key: str, value: list) -> None:
        """
        For any list value stored in cache, retrieving SHALL return equal value.
        **Validates: Requirements 7.2**
        """
        cache = LRUCache(max_size=1000)
        cache.set(key, value)
        assert cache.get(key) == value

    @settings(max_examples=100)
    @given(key=key_strategy, value=dict_value_strategy)
    def test_dict_roundtrip(self, key: str, value: dict) -> None:
        """
        For any dict value stored in cache, retrieving SHALL return equal value.
        **Validates: Requirements 7.2**
        """
        cache = LRUCache(max_size=1000)
        cache.set(key, value)
        assert cache.get(key) == value

    @settings(max_examples=50)
    @given(key=key_strategy, value=serializable_value_strategy)
    @pytest.mark.asyncio
    async def test_async_provider_roundtrip(self, key: str, value) -> None:
        """
        For any serializable value stored via async provider, retrieving SHALL return equal value.
        **Validates: Requirements 7.2**
        """
        provider = InMemoryCacheProvider()
        await provider.set(key, value, ttl=3600)
        result = await provider.get(key)
        assert result == value

    @settings(max_examples=50)
    @given(
        keys=st.lists(key_strategy, min_size=1, max_size=10, unique=True),
        values=st.lists(serializable_value_strategy, min_size=1, max_size=10),
    )
    def test_multiple_keys_roundtrip(self, keys: list[str], values: list) -> None:
        """
        For multiple key-value pairs, each SHALL be retrievable independently.
        **Validates: Requirements 7.2**
        """
        cache = LRUCache(max_size=1000)
        
        # Use min length to pair keys with values
        pairs = list(zip(keys, values))
        
        for key, value in pairs:
            cache.set(key, value)
        
        for key, value in pairs:
            assert cache.get(key) == value
