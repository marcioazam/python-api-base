"""SQLModel repository implementation.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: deep-code-quality-generics-review**
**Validates: Requirements 1.1, 14.2**
"""

from typing import Any
from collections.abc import Sequence

from pydantic import BaseModel, ValidationError
from sqlalchemy import false, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from my_api.core.exceptions import ValidationError as AppValidationError
from my_api.shared.repository import IRepository


class SQLModelRepository[T: SQLModel, CreateT: BaseModel, UpdateT: BaseModel](
    IRepository[T, CreateT, UpdateT]
):
    """SQLModel repository implementation.

    Provides CRUD operations using SQLModel and async SQLAlchemy.
    """

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

    async def get_by_id(self, id: str) -> T | None:
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

        # Apply filters
        if filters:
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

    async def update(self, id: str, data: UpdateT) -> T | None:
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

    async def delete(self, id: str, *, soft: bool = True) -> bool:
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

    async def exists(self, id: str) -> bool:
        """Check if entity exists."""
        entity = await self.get_by_id(id)
        return entity is not None
