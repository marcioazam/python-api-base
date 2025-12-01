"""Generic repository interface for CRUD operations.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: deep-code-quality-generics-review**
**Validates: Requirements 1.1, 14.3**
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any
from collections.abc import Sequence

from pydantic import BaseModel


class IRepository[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel](ABC):
    """Generic repository interface for CRUD operations.

    Provides an abstraction layer for data access with async support.
    Implementations can use any data source (SQL, NoSQL, in-memory, etc.).

    Type Parameters:
        T: Entity type.
        CreateT: DTO type for creating entities.
        UpdateT: DTO type for updating entities.
    """

    @abstractmethod
    async def get_by_id(self, id: str) -> T | None:
        """Get entity by ID.

        Args:
            id: Entity identifier.

        Returns:
            Entity if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[Sequence[T], int]:
        """Get paginated list of entities with total count.

        Args:
            skip: Number of items to skip.
            limit: Maximum number of items to return.
            filters: Optional filter criteria.
            sort_by: Field to sort by.
            sort_order: Sort order ("asc" or "desc").

        Returns:
            Tuple of (entities, total_count).
        """
        ...

    @abstractmethod
    async def create(self, data: CreateT) -> T:
        """Create new entity.

        Args:
            data: Entity creation data.

        Returns:
            Created entity with generated ID.
        """
        ...

    @abstractmethod
    async def update(self, id: str, data: UpdateT) -> T | None:
        """Update existing entity.

        Args:
            id: Entity identifier.
            data: Update data.

        Returns:
            Updated entity if found, None otherwise.
        """
        ...

    @abstractmethod
    async def delete(self, id: str, *, soft: bool = True) -> bool:
        """Delete entity.

        Args:
            id: Entity identifier.
            soft: If True, perform soft delete. If False, hard delete.

        Returns:
            True if entity was deleted, False if not found.
        """
        ...

    @abstractmethod
    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]:
        """Bulk create entities.

        Args:
            data: List of entity creation data.

        Returns:
            List of created entities.
        """
        ...

    @abstractmethod
    async def exists(self, id: str) -> bool:
        """Check if entity exists.

        Args:
            id: Entity identifier.

        Returns:
            True if entity exists, False otherwise.
        """
        ...



class InMemoryRepository[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel](
    IRepository[T, CreateT, UpdateT]
):
    """In-memory repository implementation for testing.

    Stores entities in a dictionary for fast isolated tests.
    Supports all CRUD operations with filtering and pagination.
    """

    def __init__(
        self,
        entity_type: type[T],
        id_generator: Callable[[], str] | None = None,
    ) -> None:
        """Initialize in-memory repository.

        Args:
            entity_type: Type of entity to store.
            id_generator: Optional function to generate IDs.
        """
        self._entity_type = entity_type
        self._id_generator = id_generator or self._default_id_generator
        self._storage: dict[str, T] = {}
        self._counter = 0

    def _default_id_generator(self) -> str:
        """Generate a simple incremental ID."""
        self._counter += 1
        return str(self._counter)

    async def get_by_id(self, id: str) -> T | None:
        """Get entity by ID."""
        entity = self._storage.get(id)
        if entity is None:
            return None
        # Check soft delete
        if hasattr(entity, "is_deleted") and entity.is_deleted:
            return None
        return entity

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[Sequence[T], int]:
        """Get paginated list of entities."""
        # Filter out soft-deleted entities
        entities = [
            e for e in self._storage.values()
            if not (hasattr(e, "is_deleted") and e.is_deleted)
        ]

        # Apply filters
        if filters:
            for field, value in filters.items():
                entities = [
                    e for e in entities
                    if hasattr(e, field) and getattr(e, field) == value
                ]

        total = len(entities)

        # Sort
        if sort_by:
            reverse = sort_order.lower() == "desc"
            entities = sorted(
                entities,
                key=lambda e: getattr(e, sort_by, None) or "",
                reverse=reverse,
            )

        # Paginate
        entities = entities[skip : skip + limit]

        return entities, total

    async def create(self, data: CreateT) -> T:
        """Create new entity."""
        # Convert create DTO to entity
        entity_data = data.model_dump()

        # Generate ID if not present
        if "id" not in entity_data or entity_data["id"] is None:
            entity_data["id"] = self._id_generator()

        entity = self._entity_type.model_validate(entity_data)
        self._storage[entity_data["id"]] = entity
        return entity

    async def update(self, id: str, data: UpdateT) -> T | None:
        """Update existing entity."""
        existing = await self.get_by_id(id)
        if existing is None:
            return None

        # Merge update data with existing entity
        existing_data = existing.model_dump()
        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if value is not None:
                existing_data[key] = value

        updated = self._entity_type.model_validate(existing_data)
        self._storage[id] = updated
        return updated

    async def delete(self, id: str, *, soft: bool = True) -> bool:
        """Delete entity."""
        if id not in self._storage:
            return False

        if soft:
            entity = self._storage[id]
            if hasattr(entity, "is_deleted"):
                # Perform soft delete
                entity_data = entity.model_dump()
                entity_data["is_deleted"] = True
                self._storage[id] = self._entity_type.model_validate(entity_data)
            else:
                # No soft delete support, do hard delete
                del self._storage[id]
        else:
            del self._storage[id]

        return True

    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]:
        """Bulk create entities."""
        created = []
        for item in data:
            entity = await self.create(item)
            created.append(entity)
        return created

    async def exists(self, id: str) -> bool:
        """Check if entity exists."""
        entity = await self.get_by_id(id)
        return entity is not None

    def clear(self) -> None:
        """Clear all entities from storage."""
        self._storage.clear()
        self._counter = 0
