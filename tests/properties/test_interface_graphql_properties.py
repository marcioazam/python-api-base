"""Property-based tests for interface graphql module.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 3.1, 3.2**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from pydantic import BaseModel

from interface.graphql import (
    DataLoader,
    DataLoaderConfig,
    Connection,
    Edge,
    PageInfo,
    PydanticGraphQLMapper,
)


# =============================================================================
# Strategies
# =============================================================================

key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=20,
)

value_strategy = st.integers(min_value=0, max_value=10000)


# =============================================================================
# Property 11: DataLoader Batching Behavior
# =============================================================================


class TestDataLoaderBatching:
    """Property tests for DataLoader batching.

    **Feature: interface-modules-workflow-analysis, Property 11: DataLoader Batching Behavior**
    **Validates: Requirements 3.1**
    """

    @pytest.mark.anyio
    async def test_batch_function_called_on_dispatch(self) -> None:
        """Batch function SHALL be called with accumulated keys."""
        batch_calls: list[list[str]] = []

        async def batch_fn(keys: list[str]) -> list[int | None]:
            batch_calls.append(keys)
            return [len(k) for k in keys]

        config = DataLoaderConfig(batch_size=3, cache=True)
        loader = DataLoader[str, int](batch_fn, config)

        # Load keys up to batch size
        await loader.load("a")
        await loader.load("bb")
        await loader.load("ccc")

        # Batch should have been dispatched
        assert len(batch_calls) == 1
        assert set(batch_calls[0]) == {"a", "bb", "ccc"}

    @pytest.mark.anyio
    async def test_batch_size_triggers_dispatch(self) -> None:
        """Reaching batch_size SHALL trigger dispatch."""
        dispatch_count = 0

        async def batch_fn(keys: list[str]) -> list[int | None]:
            nonlocal dispatch_count
            dispatch_count += 1
            return [1] * len(keys)

        config = DataLoaderConfig(batch_size=2, cache=True)
        loader = DataLoader[str, int](batch_fn, config)

        await loader.load("key1")
        assert dispatch_count == 0

        await loader.load("key2")
        assert dispatch_count == 1


# =============================================================================
# Property 12: DataLoader Cache Consistency
# =============================================================================


class TestDataLoaderCacheConsistency:
    """Property tests for DataLoader cache consistency.

    **Feature: interface-modules-workflow-analysis, Property 12: DataLoader Cache Consistency**
    **Validates: Requirements 3.1**
    """

    @pytest.mark.anyio
    async def test_cached_value_returned_without_batch_call(self) -> None:
        """Cached value SHALL be returned without calling batch function."""
        batch_call_count = 0

        async def batch_fn(keys: list[str]) -> list[int | None]:
            nonlocal batch_call_count
            batch_call_count += 1
            return [42] * len(keys)

        config = DataLoaderConfig(batch_size=100, cache=True)
        loader = DataLoader[str, int](batch_fn, config)

        # Prime the cache
        loader.prime("test_key", 42)

        # Load should return cached value
        result = await loader.load("test_key")

        assert result == 42
        assert batch_call_count == 0

    @pytest.mark.anyio
    async def test_cache_disabled_calls_batch_every_time(self) -> None:
        """With cache disabled, batch SHALL be called for every load."""
        batch_call_count = 0

        async def batch_fn(keys: list[str]) -> list[int | None]:
            nonlocal batch_call_count
            batch_call_count += 1
            return [1] * len(keys)

        config = DataLoaderConfig(batch_size=1, cache=False)
        loader = DataLoader[str, int](batch_fn, config)

        await loader.load("key1")
        await loader.load("key1")

        assert batch_call_count == 2


# =============================================================================
# Property 13: DataLoader Clear Removes Cache Entry
# =============================================================================


class TestDataLoaderClear:
    """Property tests for DataLoader clear.

    **Feature: interface-modules-workflow-analysis, Property 13: DataLoader Clear Removes Cache Entry**
    **Validates: Requirements 3.1**
    """

    @pytest.mark.anyio
    async def test_clear_removes_specific_key(self) -> None:
        """clear(key) SHALL remove that key from cache."""
        async def batch_fn(keys: list[str]) -> list[int | None]:
            return [len(k) for k in keys]

        config = DataLoaderConfig(batch_size=100, cache=True)
        loader = DataLoader[str, int](batch_fn, config)

        # Prime cache
        loader.prime("key1", 100)
        loader.prime("key2", 200)

        # Clear specific key
        loader.clear("key1")

        # key1 should be gone, key2 should remain
        assert loader._cache.get("key1") is None
        assert loader._cache.get("key2") == 200

    @pytest.mark.anyio
    async def test_clear_all_removes_entire_cache(self) -> None:
        """clear() without key SHALL remove all entries."""
        async def batch_fn(keys: list[str]) -> list[int | None]:
            return [1] * len(keys)

        config = DataLoaderConfig(batch_size=100, cache=True)
        loader = DataLoader[str, int](batch_fn, config)

        # Prime cache
        loader.prime("key1", 100)
        loader.prime("key2", 200)
        loader.prime("key3", 300)

        # Clear all
        loader.clear()

        assert len(loader._cache) == 0


# =============================================================================
# Property 14: DataLoader Prime Adds to Cache
# =============================================================================


class TestDataLoaderPrime:
    """Property tests for DataLoader prime.

    **Feature: interface-modules-workflow-analysis, Property 14: DataLoader Prime Adds to Cache**
    **Validates: Requirements 3.1**
    """

    @given(key=key_strategy, value=value_strategy)
    @settings(max_examples=100)
    def test_prime_adds_to_cache(self, key: str, value: int) -> None:
        """prime(key, value) SHALL add value to cache for that key."""
        assume(len(key.strip()) > 0)

        async def batch_fn(keys: list[str]) -> list[int | None]:
            return [1] * len(keys)

        config = DataLoaderConfig(batch_size=100, cache=True)
        loader = DataLoader[str, int](batch_fn, config)

        loader.prime(key, value)

        assert loader._cache[key] == value

    @given(
        keys=st.lists(key_strategy, min_size=1, max_size=10, unique=True),
        values=st.lists(value_strategy, min_size=1, max_size=10),
    )
    @settings(max_examples=100)
    def test_prime_multiple_keys(self, keys: list[str], values: list[int]) -> None:
        """Multiple prime calls SHALL add all values to cache."""
        keys = [k for k in keys if len(k.strip()) > 0]
        assume(len(keys) > 0)

        async def batch_fn(k: list[str]) -> list[int | None]:
            return [1] * len(k)

        config = DataLoaderConfig(batch_size=100, cache=True)
        loader = DataLoader[str, int](batch_fn, config)

        for key, value in zip(keys, values):
            loader.prime(key, value)

        for key, value in zip(keys, values):
            assert loader._cache[key] == value


# =============================================================================
# Property 15: Relay Connection Edge Count
# =============================================================================


class TestRelayConnectionEdgeCount:
    """Property tests for Relay Connection edge count.

    **Feature: interface-modules-workflow-analysis, Property 15: Relay Connection Edge Count**
    **Validates: Requirements 3.2**
    """

    @given(items=st.lists(st.integers(), min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_edge_count_equals_items(self, items: list[int]) -> None:
        """Connection edges count SHALL equal number of items."""
        edges = [Edge(node=item, cursor=str(i)) for i, item in enumerate(items)]
        page_info = PageInfo(
            has_next_page=False,
            has_previous_page=False,
            start_cursor=edges[0].cursor if edges else None,
            end_cursor=edges[-1].cursor if edges else None,
        )
        connection = Connection(edges=edges, page_info=page_info, total_count=len(items))

        assert len(connection.edges) == len(items)


# =============================================================================
# Property 16: Relay PageInfo Consistency
# =============================================================================


class TestRelayPageInfoConsistency:
    """Property tests for Relay PageInfo consistency.

    **Feature: interface-modules-workflow-analysis, Property 16: Relay PageInfo Consistency**
    **Validates: Requirements 3.2**
    """

    def test_empty_edges_has_none_cursors(self) -> None:
        """If edges is empty, start_cursor and end_cursor SHALL be None."""
        page_info = PageInfo(
            has_next_page=False,
            has_previous_page=False,
            start_cursor=None,
            end_cursor=None,
        )
        connection = Connection[int](edges=[], page_info=page_info, total_count=0)

        assert connection.page_info.start_cursor is None
        assert connection.page_info.end_cursor is None

    @given(items=st.lists(st.integers(), min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_non_empty_edges_has_cursors(self, items: list[int]) -> None:
        """If edges is not empty, start_cursor and end_cursor SHALL be set."""
        edges = [Edge(node=item, cursor=str(i)) for i, item in enumerate(items)]
        page_info = PageInfo(
            has_next_page=False,
            has_previous_page=False,
            start_cursor=edges[0].cursor,
            end_cursor=edges[-1].cursor,
        )
        connection = Connection(edges=edges, page_info=page_info, total_count=len(items))

        assert connection.page_info.start_cursor is not None
        assert connection.page_info.end_cursor is not None
        assert connection.page_info.start_cursor == edges[0].cursor
        assert connection.page_info.end_cursor == edges[-1].cursor


# =============================================================================
# Property 17: PydanticGraphQLMapper Type Mapping
# =============================================================================


class SimpleModel(BaseModel):
    """Simple model for mapper tests."""

    name: str
    count: int
    price: float
    active: bool


class TestPydanticGraphQLMapperTypeMapping:
    """Property tests for PydanticGraphQLMapper type mapping.

    **Feature: interface-modules-workflow-analysis, Property 17: PydanticGraphQLMapper Type Mapping**
    **Validates: Requirements 3.1**
    """

    def test_string_maps_to_string(self) -> None:
        """str fields SHALL map to GraphQL String."""
        mapper = PydanticGraphQLMapper[SimpleModel](SimpleModel)
        assert "String" in mapper._field_types["name"]

    def test_int_maps_to_int(self) -> None:
        """int fields SHALL map to GraphQL Int."""
        mapper = PydanticGraphQLMapper[SimpleModel](SimpleModel)
        assert "Int" in mapper._field_types["count"]

    def test_float_maps_to_float(self) -> None:
        """float fields SHALL map to GraphQL Float."""
        mapper = PydanticGraphQLMapper[SimpleModel](SimpleModel)
        assert "Float" in mapper._field_types["price"]

    def test_bool_maps_to_boolean(self) -> None:
        """bool fields SHALL map to GraphQL Boolean."""
        mapper = PydanticGraphQLMapper[SimpleModel](SimpleModel)
        assert "Boolean" in mapper._field_types["active"]


# =============================================================================
# Property 18: GraphQL Schema Generation
# =============================================================================


class TestGraphQLSchemaGeneration:
    """Property tests for GraphQL schema generation.

    **Feature: interface-modules-workflow-analysis, Property 18: GraphQL Schema Generation**
    **Validates: Requirements 3.1**
    """

    def test_schema_contains_type_name(self) -> None:
        """to_graphql_schema SHALL include model name as type name."""
        mapper = PydanticGraphQLMapper[SimpleModel](SimpleModel)
        schema = mapper.to_graphql_schema()

        assert "type SimpleModel" in schema

    def test_schema_contains_all_fields(self) -> None:
        """to_graphql_schema SHALL include all model fields."""
        mapper = PydanticGraphQLMapper[SimpleModel](SimpleModel)
        schema = mapper.to_graphql_schema()

        assert "name:" in schema
        assert "count:" in schema
        assert "price:" in schema
        assert "active:" in schema

    def test_schema_is_valid_graphql_format(self) -> None:
        """to_graphql_schema SHALL produce valid GraphQL type definition."""
        mapper = PydanticGraphQLMapper[SimpleModel](SimpleModel)
        schema = mapper.to_graphql_schema()

        # Should have opening and closing braces
        assert schema.startswith("type SimpleModel {")
        assert schema.endswith("}")

        # Should have field definitions
        lines = schema.split("\n")
        assert len(lines) >= 3  # type line + at least one field + closing brace
