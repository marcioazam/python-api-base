"""GraphQL resolver protocols and base classes.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 20.2, 20.3, 20.4**
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from core.base.patterns.result import Result
from interface.graphql.relay import Connection, Edge, PageInfo


@dataclass
class QueryArgs:
    """Base query arguments."""

    first: int | None = None
    after: str | None = None
    filter: dict[str, Any] | None = None


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
        """Resolve the query."""
        ...


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
    ) -> Connection[T]:
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
        """Resolve the mutation."""
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
        from core.base.patterns.result import Ok

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
        """Subscribe to events."""
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
