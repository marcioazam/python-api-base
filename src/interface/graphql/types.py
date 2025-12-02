"""Generic GraphQL support with PEP 695 type parameters.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from core.base.result import Result


@runtime_checkable
class GraphQLType[T: BaseModel](Protocol):
    """Protocol for GraphQL type mapping from Pydantic models.

    Type Parameters:
        T: The Pydantic model type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.1**
    """

    @classmethod
    def from_pydantic(cls, model: type[T]) -> "GraphQLType[T]":
        """Create GraphQL type from Pydantic model."""
        ...

    def to_graphql_schema(self) -> str:
        """Generate GraphQL schema definition."""
        ...

    def get_field_resolvers(self) -> dict[str, Callable]:
        """Get field resolvers for this type."""
        ...


class PydanticGraphQLMapper[T: BaseModel]:
    """Maps Pydantic models to GraphQL types.

    Type Parameters:
        T: The Pydantic model type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.1**
    """

    def __init__(self, model: type[T]) -> None:
        self._model = model
        self._field_types = self._extract_field_types()

    def _extract_field_types(self) -> dict[str, str]:
        """Extract field types from Pydantic model."""
        type_map = {
            str: "String",
            int: "Int",
            float: "Float",
            bool: "Boolean",
            list: "List",
        }
        fields = {}
        for name, field_info in self._model.model_fields.items():
            annotation = field_info.annotation
            graphql_type = type_map.get(annotation, "String")
            is_required = field_info.is_required()
            fields[name] = f"{graphql_type}{'!' if is_required else ''}"
        return fields

    def to_graphql_schema(self) -> str:
        """Generate GraphQL schema definition."""
        type_name = self._model.__name__
        fields_str = "\n  ".join(
            f"{name}: {gql_type}" for name, gql_type in self._field_types.items()
        )
        return f"type {type_name} {{\n  {fields_str}\n}}"


@runtime_checkable
class QueryResolver[T, TArgs](Protocol):
    """Generic query resolver protocol with typed arguments.

    Type Parameters:
        T: The return type of the query.
        TArgs: The argument type for the query.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.2**
    """

    async def resolve(self, args: TArgs, context: Any) -> T | list[T] | None:
        """Resolve the query.

        Args:
            args: Query arguments.
            context: GraphQL context.

        Returns:
            Query result.
        """
        ...


@dataclass
class QueryArgs:
    """Base query arguments."""

    first: int | None = None
    after: str | None = None
    filter: dict[str, Any] | None = None


class BaseQueryResolver[T: BaseModel, TArgs](ABC):
    """Base class for query resolvers.

    Type Parameters:
        T: The return type.
        TArgs: The argument type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.2**
    """

    @abstractmethod
    async def resolve(self, args: TArgs, context: Any) -> T | list[T] | None:
        """Resolve the query."""
        ...

    async def resolve_connection(
        self,
        args: TArgs,
        context: Any,
    ) -> "Connection[T]":
        """Resolve as a Relay-style connection."""
        items = await self.resolve(args, context)
        if items is None:
            items = []
        elif not isinstance(items, list):
            items = [items]

        edges = [Edge(node=item, cursor=str(i)) for i, item in enumerate(items)]
        return Connection(
            edges=edges,
            page_info=PageInfo(
                has_next_page=False,
                has_previous_page=False,
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
            ),
        )


@runtime_checkable
class MutationResolver[TInput: BaseModel, TOutput](Protocol):
    """Generic mutation resolver with validation.

    Type Parameters:
        TInput: The input type for the mutation.
        TOutput: The output type of the mutation.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.3**
    """

    async def resolve(
        self,
        input_data: TInput,
        context: Any,
    ) -> Result[TOutput, Exception]:
        """Resolve the mutation.

        Args:
            input_data: Validated input data.
            context: GraphQL context.

        Returns:
            Result with output or error.
        """
        ...

    def validate(self, input_data: TInput) -> Result[TInput, Exception]:
        """Validate input data."""
        ...


class BaseMutationResolver[TInput: BaseModel, TOutput](ABC):
    """Base class for mutation resolvers with validation.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.3**
    """

    @abstractmethod
    async def resolve(
        self,
        input_data: TInput,
        context: Any,
    ) -> Result[TOutput, Exception]:
        """Resolve the mutation."""
        ...

    def validate(self, input_data: TInput) -> Result[TInput, Exception]:
        """Default validation using Pydantic."""
        from core.base.result import Ok

        return Ok(input_data)


@runtime_checkable
class Subscription[T](Protocol):
    """Generic subscription with typed event streams.

    Type Parameters:
        T: The type of events in the stream.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.4**
    """

    async def subscribe(self, context: Any) -> AsyncIterator[T]:
        """Subscribe to events.

        Args:
            context: GraphQL context.

        Yields:
            Stream of typed events.
        """
        ...


class BaseSubscription[T](ABC):
    """Base class for subscriptions.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.4**
    """

    @abstractmethod
    async def subscribe(self, context: Any) -> AsyncIterator[T]:
        """Subscribe to events."""
        ...


@dataclass
class DataLoaderConfig:
    """DataLoader configuration."""

    batch_size: int = 100
    cache: bool = True


class DataLoader[TKey, TValue]:
    """Generic DataLoader for N+1 prevention.

    Type Parameters:
        TKey: The key type for loading.
        TValue: The value type returned.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.5**
    """

    def __init__(
        self,
        batch_fn: Callable[[list[TKey]], Awaitable[list[TValue | None]]],
        config: DataLoaderConfig | None = None,
    ) -> None:
        self._batch_fn = batch_fn
        self._config = config or DataLoaderConfig()
        self._cache: dict[TKey, TValue] = {}
        self._queue: list[TKey] = []
        self._pending: dict[TKey, list[Callable[[TValue | None], None]]] = {}

    async def load(self, key: TKey) -> TValue | None:
        """Load a single value by key.

        Args:
            key: The key to load.

        Returns:
            The loaded value or None.
        """
        # Check cache
        if self._config.cache and key in self._cache:
            return self._cache[key]

        # Add to batch and await
        self._queue.append(key)

        if len(self._queue) >= self._config.batch_size:
            await self._dispatch()

        # Check cache again after dispatch
        return self._cache.get(key)

    async def load_many(self, keys: list[TKey]) -> list[TValue | None]:
        """Load multiple values by keys.

        Args:
            keys: The keys to load.

        Returns:
            List of loaded values (or None for missing).
        """
        results: list[TValue | None] = []
        for key in keys:
            result = await self.load(key)
            results.append(result)
        return results

    async def _dispatch(self) -> None:
        """Dispatch batch load."""
        if not self._queue:
            return

        keys = list(self._queue)
        self._queue.clear()

        values = await self._batch_fn(keys)

        for key, value in zip(keys, values):
            if value is not None and self._config.cache:
                self._cache[key] = value

    def clear(self, key: TKey | None = None) -> None:
        """Clear cache for key or all."""
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]

    def prime(self, key: TKey, value: TValue) -> None:
        """Prime cache with a value."""
        self._cache[key] = value


# Relay Connection Types
@dataclass
class PageInfo:
    """Relay-style page info."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None = None
    end_cursor: str | None = None


@dataclass
class Edge[T]:
    """Relay-style edge."""

    node: T
    cursor: str


@dataclass
class Connection[T]:
    """Relay-style connection."""

    edges: list[Edge[T]]
    page_info: PageInfo
    total_count: int | None = None
