"""SQLModel repository implementation.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: deep-code-quality-generics-review**
**Validates: Requirements 1.1, 14.2**
"""

from collections.abc import Sequence
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import false, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from core.base.repository import IRepository
from core.errors import ValidationError as AppValidationError


class SQLModelRepository[
    T: SQLModel,
    CreateT: BaseModel,
    UpdateT: BaseModel,
    IdType: (str, int) = str,
](IRepository[T, CreateT, UpdateT, IdType]):
    """SQLModel repository implementation.

    Provides CRUD operations using SQLModel and async SQLAlchemy.

    Security:
        To prevent SQL injection through dynamic filters, subclasses MUST define
        _allowed_filter_fields containing the whitelist of fields that can be filtered.

        Example:
            class UserRepository(SQLModelRepository[User, CreateUserDTO, UpdateUserDTO, str]):
                _allowed_filter_fields: ClassVar[set[str]] = {"email", "username", "is_active"}
    """

    # Whitelist of fields allowed for filtering (prevents SQL injection)
    # Subclasses MUST override this to enable filtering
    _allowed_filter_fields: ClassVar[set[str]] = set()

    def __init__(
        self,
        session: AsyncSession,
        model_class: type[T],
    ) -> None:
        """Initialize SQLModel repository.

        Args:
            session: Async database session.
            model_class: SQLModel class for this repository.
        """
        self._session = session
        self._model_class = model_class

    async def get_by_id(self, id: IdType) -> T | None:
        """Get entity by ID.

        Args:
            id: Entity identifier.

        Returns:
            Entity if found and not soft-deleted, None otherwise.
        """
        statement = select(self._model_class).where(self._model_class.id == id)
        if hasattr(self._model_class, "is_deleted"):
            statement = statement.where(self._model_class.is_deleted.is_(false()))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[Sequence[T], int]:
        """Get paginated list of entities.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            filters: Optional field filters.
            sort_by: Field to sort by.
            sort_order: Sort direction ('asc' or 'desc').

        Returns:
            Tuple of (entities list, total count).
        """
        # Base query excluding soft-deleted
        base_query = select(self._model_class)
        if hasattr(self._model_class, "is_deleted"):
            base_query = base_query.where(self._model_class.is_deleted.is_(false()))

        # Apply filters with security validation
        if filters:
            # Validate filters against whitelist to prevent SQL injection
            invalid_fields = set(filters.keys()) - self._allowed_filter_fields
            if invalid_fields:
                msg = (
                    f"Filtering by fields {invalid_fields} not allowed. "
                    f"Allowed fields: {self._allowed_filter_fields or 'None (filtering disabled)'}. "
                    f"Override _allowed_filter_fields in {self.__class__.__name__} to enable filtering."
                )
                raise AppValidationError(msg)

            for field, value in filters.items():
                if hasattr(self._model_class, field):
                    base_query = base_query.where(
                        getattr(self._model_class, field) == value
                    )

        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        if sort_by and hasattr(self._model_class, sort_by):
            order_column = getattr(self._model_class, sort_by)
            if sort_order.lower() == "desc":
                order_column = order_column.desc()
            base_query = base_query.order_by(order_column)

        # Apply pagination
        base_query = base_query.offset(skip).limit(limit)

        # Execute
        result = await self._session.execute(base_query)
        entities = list(result.scalars().all())

        return entities, total

    async def create(self, data: CreateT) -> T:
        """Create new entity.

        Args:
            data: DTO with entity data.

        Returns:
            Created entity.

        Raises:
            AppValidationError: If data validation fails.
        """
        try:
            entity_data = data.model_dump()
            entity = self._model_class.model_validate(entity_data)
        except ValidationError as e:
            raise AppValidationError(
                message="Entity validation failed",
                details={"errors": e.errors()},
            ) from e

        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, id: IdType, data: UpdateT) -> T | None:
        """Update existing entity."""
        entity = await self.get_by_id(id)
        if entity is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None and hasattr(entity, field):
                setattr(entity, field, value)

        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: IdType, *, soft: bool = True) -> bool:
        """Delete entity."""
        entity = await self.get_by_id(id)
        if entity is None:
            return False

        if soft and hasattr(entity, "is_deleted"):
            entity.is_deleted = True
            self._session.add(entity)
        else:
            await self._session.delete(entity)

        await self._session.flush()
        return True

    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]:
        """Bulk create entities."""
        entities = []
        for item in data:
            entity_data = item.model_dump()
            entity = self._model_class.model_validate(entity_data)
            self._session.add(entity)
            entities.append(entity)

        await self._session.flush()
        for entity in entities:
            await self._session.refresh(entity)

        return entities

    async def exists(self, id: IdType) -> bool:
        """Check if entity exists."""
        entity = await self.get_by_id(id)
        return entity is not None

    async def bulk_update(
        self,
        updates: Sequence[tuple[IdType, UpdateT]],
    ) -> Sequence[T]:
        """Bulk update entities.

        Args:
            updates: Sequence of (id, update_data) tuples.

        Returns:
            Sequence of updated entities.

        **Feature: python-api-base-2025-review**
        **Validates: Requirements 1.4**
        """
        updated_entities: list[T] = []

        for entity_id, data in updates:
            entity = await self.get_by_id(entity_id)
            if entity is None:
                continue

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if value is not None and hasattr(entity, field):
                    setattr(entity, field, value)

            self._session.add(entity)
            updated_entities.append(entity)

        await self._session.flush()

        for entity in updated_entities:
            await self._session.refresh(entity)

        return updated_entities

    async def bulk_delete(
        self,
        ids: Sequence[IdType],
        *,
        soft: bool = True,
    ) -> int:
        """Bulk delete entities.

        Args:
            ids: Sequence of entity IDs to delete.
            soft: If True, soft delete; otherwise hard delete.

        Returns:
            Number of entities deleted.

        **Feature: python-api-base-2025-review**
        **Validates: Requirements 1.4**
        """
        deleted_count = 0

        for entity_id in ids:
            entity = await self.get_by_id(entity_id)
            if entity is None:
                continue

            if soft and hasattr(entity, "is_deleted"):
                entity.is_deleted = True
                self._session.add(entity)
            else:
                await self._session.delete(entity)

            deleted_count += 1

        await self._session.flush()
        return deleted_count

    async def count(
        self,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count entities matching filters.

        Args:
            filters: Optional field filters.

        Returns:
            Count of matching entities.

        **Feature: python-api-base-2025-review**
        **Validates: Requirements 1.4**
        """
        query = select(func.count()).select_from(self._model_class)

        if hasattr(self._model_class, "is_deleted"):
            query = query.where(self._model_class.is_deleted.is_(false()))

        if filters:
            for field, value in filters.items():
                if hasattr(self._model_class, field):
                    query = query.where(getattr(self._model_class, field) == value)

        result = await self._session.execute(query)
        return result.scalar() or 0
