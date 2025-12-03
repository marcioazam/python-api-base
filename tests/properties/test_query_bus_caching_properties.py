"""Property-based tests for QueryBus caching behavior.

**Feature: architecture-restructuring-2025, Property 5: QueryBus Dispatches with Caching**
**Validates: Requirements 3.2, 3.4**
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

try:
    from application.common.bus import QueryBus, Query, HandlerNotFoundError
except ImportError:
    pytest.skip("my_app.application.common.bus not available", allow_module_level=True)


class InMemoryCache:
    """Simple in-memory cache for testing."""
    
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._call_count: int = 0
    
    async def get(self, key: str) -> Any | None:
        return self._store.get(key)
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._store[key] = value
        self._call_count += 1
    
    def clear(self) -> None:
        self._store.clear()
        self._call_count = 0


@dataclass
class CacheableQuery(Query[str]):
    """Test query for property tests."""
    query_id: str
    cacheable: bool = True
    cache_ttl: int | None = 60
    
    async def execute(self) -> str:
        return f"result-{self.query_id}"


@dataclass
class NonCacheableQuery(Query[str]):
    """Query that should not be cached."""
    query_id: str
    cacheable: bool = False
    
    async def execute(self) -> str:
        return f"result-{self.query_id}"


class TestQueryBusCachingProperties:
    """Property tests for QueryBus caching behavior."""

    @settings(max_examples=10)
    @given(query_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))))
    def test_cached_query_returns_same_result(self, query_id: str) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 5: QueryBus Dispatches with Caching**
        
        For any cacheable query, dispatching the same query twice SHALL return
        the same result, with the second call using the cached value.
        **Validates: Requirements 3.2, 3.4**
        """
        async def run_test() -> None:
            bus = QueryBus()
            cache = InMemoryCache()
            bus.set_cache(cache)
            
            call_count = 0
            
            async def handler(query: CacheableQuery) -> str:
                nonlocal call_count
                call_count += 1
                return f"result-{query.query_id}"
            
            bus.register(CacheableQuery, handler)
            
            query = CacheableQuery(query_id=query_id)
            
            # First dispatch - should call handler
            result1 = await bus.dispatch(query)
            
            # Second dispatch - should use cache
            result2 = await bus.dispatch(query)
            
            # Results should be identical
            assert result1 == result2
            # Handler should only be called once (second call uses cache)
            assert call_count == 1
        
        asyncio.new_event_loop().run_until_complete(run_test())

    @settings(max_examples=10)
    @given(query_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))))
    def test_non_cacheable_query_always_executes_handler(self, query_id: str) -> None:
        """
        For any non-cacheable query, dispatching SHALL always execute the handler.
        **Validates: Requirements 3.2**
        """
        async def run_test() -> None:
            bus = QueryBus()
            cache = InMemoryCache()
            bus.set_cache(cache)
            
            call_count = 0
            
            async def handler(query: NonCacheableQuery) -> str:
                nonlocal call_count
                call_count += 1
                return f"result-{query.query_id}-{call_count}"
            
            bus.register(NonCacheableQuery, handler)
            
            query = NonCacheableQuery(query_id=query_id)
            
            # Both dispatches should call handler
            await bus.dispatch(query)
            await bus.dispatch(query)
            
            assert call_count == 2
        
        asyncio.new_event_loop().run_until_complete(run_test())

    @settings(max_examples=10)
    @given(
        query_ids=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L", "N"))),
            min_size=2,
            max_size=3,
            unique=True
        )
    )
    def test_different_queries_have_different_cache_keys(self, query_ids: list[str]) -> None:
        """
        For any set of queries with different parameters, each SHALL have
        a unique cache key.
        **Validates: Requirements 3.4**
        """
        async def run_test() -> None:
            bus = QueryBus()
            cache = InMemoryCache()
            bus.set_cache(cache)
            
            async def handler(query: CacheableQuery) -> str:
                return f"result-{query.query_id}"
            
            bus.register(CacheableQuery, handler)
            
            results = []
            for qid in query_ids:
                query = CacheableQuery(query_id=qid)
                result = await bus.dispatch(query)
                results.append(result)
            
            # All results should be unique
            assert len(set(results)) == len(query_ids)
        
        asyncio.new_event_loop().run_until_complete(run_test())

    @settings(max_examples=10)
    @given(query_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))))
    def test_query_without_cache_executes_normally(self, query_id: str) -> None:
        """
        For any query when no cache is configured, dispatch SHALL execute
        the handler directly.
        **Validates: Requirements 3.2**
        """
        async def run_test() -> None:
            bus = QueryBus()
            # No cache set
            
            call_count = 0
            
            async def handler(query: CacheableQuery) -> str:
                nonlocal call_count
                call_count += 1
                return f"result-{query.query_id}"
            
            bus.register(CacheableQuery, handler)
            
            query = CacheableQuery(query_id=query_id)
            result = await bus.dispatch(query)
            
            assert result == f"result-{query_id}"
            assert call_count == 1
        
        asyncio.new_event_loop().run_until_complete(run_test())

    def test_unregistered_query_raises_error(self) -> None:
        """
        For any query without a registered handler, dispatch SHALL raise
        HandlerNotFoundError.
        **Validates: Requirements 3.2**
        """
        async def run_test() -> None:
            bus = QueryBus()
            query = CacheableQuery(query_id="test")
            
            with pytest.raises(HandlerNotFoundError):
                await bus.dispatch(query)
        
        asyncio.new_event_loop().run_until_complete(run_test())

    @settings(max_examples=10)
    @given(query_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))))
    def test_cache_key_generation_is_deterministic(self, query_id: str) -> None:
        """
        For any query, the cache key generation SHALL be deterministic -
        the same query parameters SHALL always produce the same cache key.
        **Validates: Requirements 3.4**
        """
        bus = QueryBus()
        
        query1 = CacheableQuery(query_id=query_id)
        query2 = CacheableQuery(query_id=query_id)
        
        key1 = bus._get_cache_key(query1)
        key2 = bus._get_cache_key(query2)
        
        assert key1 == key2
        assert key1 is not None
