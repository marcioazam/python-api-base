"""Generic GraphQL resolvers for CRUD operations.

This module provides base resolver classes that can be extended
to create type-safe GraphQL resolvers for any entity type.

**Feature: api-architecture-analysis, Task 3.1: GraphQL Support with Strawberry**
**Validates: Requirements 4.5**
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from my_api.adapters.api.graphql.types import (
    Connection,
    ConnectionArgs,
    connection_from_list,
)
from my_api.shared.repository import IRepository


class BaseResolver[T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel, GraphQLType](ABC):
    """Base resolver for GraphQL CRUD operations.

    Provides generic implementations for common GraphQL operations
    that can be customized for specific entity types.

    Type Parameters:
        T: The entity type.
        CreateDTO: DTO type for creating entities.
        UpdateDTO: DTO type for updating entities.
        GraphQLType: The Strawberry type for GraphQL responses.
    """

    def __init__(
        self,
        repository: IRepository[T, CreateDTO, UpdateDTO],
    ) -> None:
        """Initialize the resolver.

        Args:
            repository: Repository for data operations.
        """
        self._repository = repository

    @abstractmethod
    def to_graphql_type(self, entity: T) -> GraphQLType:
        """Convert an entity to its GraphQL type representation.

        Args:
            entity: The entity to convert.

        Returns:
            The GraphQL type representation.
        """
        ...

    async def get_by_id(self, id: str) -> GraphQLType | None:
        """Get a single entity by ID.

        Args:
            id: The entity identifier.

        Returns:
            The entity as GraphQL type, or None if not found.
        """
        entity = await self._repository.get_by_id(id)
        if entity is None:
            return None
        return self.to_graphql_type(entity)

    async def get_all(
        self,
        args: ConnectionArgs | None = None,
        filters: dict | None = None,
    ) -> Connection[GraphQLType]:
        """Get all entities with pagination.

        Args:
            args: Pagination arguments.
            filters: Optional filter criteria.

        Returns:
            A Connection containing the paginated entities.
        """
        # Get all entities (in production, apply pagination at DB level)
        entities, total = await self._repository.get_all(
            skip=0,
            limit=1000,  # Max limit for safety
            filters=filters,
        )

        # Convert to GraphQL types
        graphql_items = [self.to_graphql_type(e) for e in entities]

        return connection_from_list(
            items=graphql_items,
            args=args,
            total_count=total,
        )

    async def create(self, input_data: CreateDTO) -> GraphQLType:
        """Create a new entity.

        Args:
            input_data: The creation data.

        Returns:
            The created entity as GraphQL type.
        """
        entity = await self._repository.create(input_data)
        return self.to_graphql_type(entity)

    async def update(
        self, id: str, input_data: UpdateDTO
    ) -> GraphQLType | None:
        """Update an existing entity.

        Args:
            id: The entity identifier.
            input_data: The update data.

        Returns:
            The updated entity as GraphQL type, or None if not found.
        """
        entity = await self._repository.update(id, input_data)
        if entity is None:
            return None
        return self.to_graphql_type(entity)

    async def delete(self, id: str) -> bool:
        """Delete an entity.

        Args:
            id: The entity identifier.

        Returns:
            True if deleted, False if not found.
        """
        return await self._repository.delete(id)


class ReadOnlyResolver[T: BaseModel, GraphQLType](ABC):
    """Read-only resolver for GraphQL queries.

    Provides generic implementations for read operations only.

    Type Parameters:
        T: The entity type.
        GraphQLType: The Strawberry type for GraphQL responses.
    """

    def __init__(
        self,
        repository: IRepository[T, BaseModel, BaseModel],
    ) -> None:
        """Initialize the resolver.

        Args:
            repository: Repository for data operations.
        """
        self._repository = repository

    @abstractmethod
    def to_graphql_type(self, entity: T) -> GraphQLType:
        """Convert an entity to its GraphQL type representation."""
        ...

    async def get_by_id(self, id: str) -> GraphQLType | None:
        """Get a single entity by ID."""
        entity = await self._repository.get_by_id(id)
        if entity is None:
            return None
        return self.to_graphql_type(entity)

    async def get_all(
        self,
        first: int | None = None,
        after: str | None = None,
        last: int | None = None,
        before: str | None = None,
    ) -> Connection[GraphQLType]:
        """Get all entities with Relay-style pagination."""
        entities, total = await self._repository.get_all(
            skip=0,
            limit=1000,
        )

        graphql_items = [self.to_graphql_type(e) for e in entities]
        args = ConnectionArgs(
            first=first,
            after=after,
            last=last,
            before=before,
        )

        return connection_from_list(
            items=graphql_items,
            args=args,
            total_count=total,
        )
