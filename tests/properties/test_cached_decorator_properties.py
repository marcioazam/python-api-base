"""Property-based tests for Cached Decorator Returns Cached Results.

**Feature: architecture-restructuring-2025, Property 10: Cached Decorator Returns Cached Results**
**Validates: Requirements 7.4**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

try:
    from my_app.infrastructure.cache.decorators import cached, get_default_cache
    from my_app.infrastructure.cache.providers import InMemoryCacheProvider
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


int_strategy = st.integers(min_value=0, max_value=1000)
string_strategy = st.text(min_size=1, max_size=50)


class TestCachedDecorator:
    """Property tests for @cached decorator."""

    @settings(max_examples=50)
    @given(x=int_strategy, y=int_strategy)
    @pytest.mark.asyncio
    async def test_cached_async_function_returns_same_result(self, x: int, y: int) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 10: Cached Decorator Returns Cached Results**
        
        For any async function decorated with @cached, calling twice with same args
        SHALL return the same result.
        **Validates: Requirements 7.4**
        """
        call_count = 0
        cache = InMemoryCacheProvider()
        
        @cached(ttl=3600, cache_provider=cache)
        async def add_numbers(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b
        
        result1 = await add_numbers(x, y)
        result2 = await add_numbers(x, y)
        
        assert result1 == result2
        assert result1 == x + y

    @settings(max_examples=50)
    @given(x=int_strategy)
    @pytest.mark.asyncio
    async def test_cached_function_called_once_for_same_args(self, x: int) -> None:
        """
        For any function decorated with @cached, the underlying function
        SHALL be called only once for the same arguments within TTL.
        **Validates: Requirements 7.4**
        """
        call_count = 0
        cache = InMemoryCacheProvider()
        
        @cached(ttl=3600, cache_provider=cache)
        async def expensive_computation(n: int) -> int:
            nonlocal call_count
            call_count += 1
            return n * n
        
        # Call multiple times with same argument
        await expensive_computation(x)
        await expensive_computation(x)
        await expensive_computation(x)
        
        # Function should only be called once
        assert call_count == 1

    @settings(max_examples=30)
    @given(values=st.lists(int_strategy, min_size=2, max_size=5, unique=True))
    @pytest.mark.asyncio
    async def test_different_args_call_function_separately(self, values: list[int]) -> None:
        """
        For different arguments, the cached function SHALL be called for each unique set.
        **Validates: Requirements 7.4**
        """
        call_count = 0
        cache = InMemoryCacheProvider()
        
        @cached(ttl=3600, cache_provider=cache)
        async def square(n: int) -> int:
            nonlocal call_count
            call_count += 1
            return n * n
        
        results = []
        for v in values:
            results.append(await square(v))
        
        # Each unique value should trigger one call
        assert call_count == len(values)
        
        # Results should be correct
        for v, r in zip(values, results):
            assert r == v * v

    @settings(max_examples=30)
    @given(key=string_strategy, value=int_strategy)
    @pytest.mark.asyncio
    async def test_custom_key_function(self, key: str, value: int) -> None:
        """
        For @cached with custom key_fn, the key function SHALL determine cache key.
        **Validates: Requirements 7.4**
        """
        call_count = 0
        cache = InMemoryCacheProvider()
        
        @cached(ttl=3600, key_fn=lambda k, v: f"custom:{k}", cache_provider=cache)
        async def process(k: str, v: int) -> str:
            nonlocal call_count
            call_count += 1
            return f"{k}={v}"
        
        result1 = await process(key, value)
        result2 = await process(key, value + 1)  # Different value, same key
        
        # Should return cached result because key is same
        assert result1 == result2
        assert call_count == 1

    @settings(max_examples=20)
    @given(x=int_strategy)
    @pytest.mark.asyncio
    async def test_cache_preserves_return_type(self, x: int) -> None:
        """
        For any cached function, the return type SHALL be preserved.
        **Validates: Requirements 7.4**
        """
        cache = InMemoryCacheProvider()
        
        @cached(ttl=3600, cache_provider=cache)
        async def get_dict(n: int) -> dict:
            return {"value": n, "squared": n * n}
        
        result1 = await get_dict(x)
        result2 = await get_dict(x)
        
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert result1 == result2
        assert result1["value"] == x
        assert result1["squared"] == x * x
