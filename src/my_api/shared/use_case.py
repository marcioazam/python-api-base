"""Generic use case base class for business logic.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
Uses @overload for type narrowing on methods with conditional return types.
"""

from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import Any, Literal, overload
from collections.abc import AsyncGenerator

from pydantic import BaseModel

from my_api.core.exceptions import EntityNotFoundError
from my_api.shared.dto import PaginatedResponse
from my_api.shared.mapper import IMapper
from my_api.shared.repository import IRepository
from my_api.shared.unit_of_work import IUnitOfWork


class BaseUseCase[
    T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel, ResponseDTO: BaseModel
]:
    """Generic use case with CRUD operations.

    Encapsulates business logic and delegates data operations to repository.
    Uses mapper for DTO-to-entity conversions.

    Type Parameters:
        T: Entity type.
        CreateDTO: DTO type for creating entities.
        UpdateDTO: DTO type for updating entities.
        ResponseDTO: DTO type for responses.
    """

    def __init__(
        self,
        repository: IRepository[T, CreateDTO, UpdateDTO],
        mapper: IMapper[T, ResponseDTO],
        entity_name: str = "Entity",
        unit_of_work: IUnitOfWork | None = None,
    ) -> None:
        """Initialize use case.

        Args:
            repository: Repository for data operations.
            mapper: Mapper for DTO conversions.
            entity_name: Name of entity for error messages.
            unit_of_work: Optional Unit of Work for transaction management.
        """
        self._repository = repository
        self._mapper = mapper
        self._entity_name = entity_name
        self._uow = unit_of_work

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None, None]:
        """Execute operations within a transaction.

        If a Unit of Work is configured, wraps operations in a transaction.
        Otherwise, operations execute without explicit transaction management.

        Usage:
            async with use_case.transaction():
                await use_case.create(data1)
                await use_case.create(data2)
            # Auto-commits on success, rollbacks on error

        Yields:
            None
        """
        if self._uow is None:
            yield
            return

        async with self._uow:
            try:
                yield
                await self._uow.commit()
            except Exception:
                await self._uow.rollback()
                raise

    @overload
    async def get(
        self, id: str, *, raise_on_missing: Literal[True] = True
    ) -> ResponseDTO: ...

    @overload
    async def get(
        self, id: str, *, raise_on_missing: Literal[False]
    ) -> ResponseDTO | None: ...

    async def get(
        self, id: str, *, raise_on_missing: bool = True
    ) -> ResponseDTO | None:
        """Get entity by ID with type-narrowed return type.

        Uses @overload for precise type inference:
        - get(id) or get(id, raise_on_missing=True) -> ResponseDTO (never None)
        - get(id, raise_on_missing=False) -> ResponseDTO | None

        Args:
            id: Entity identifier.
            raise_on_missing: If True (default), raises EntityNotFoundError when
                entity is not found. If False, returns None instead.

        Returns:
            ResponseDTO: Entity as response DTO.
            None: Only when raise_on_missing=False and entity not found.

        Raises:
            EntityNotFoundError: If entity not found and raise_on_missing=True.

        Examples:
            # Type is ResponseDTO (guaranteed non-None)
            item = await use_case.get("123")

            # Type is ResponseDTO | None
            item = await use_case.get("123", raise_on_missing=False)
            if item is not None:
                print(item.name)
        """
        entity = await self._repository.get_by_id(id)
        if entity is None:
            if raise_on_missing:
                raise EntityNotFoundError(self._entity_name, id)
            return None
        return self._mapper.to_dto(entity)

    async def get_or_none(self, id: str) -> ResponseDTO | None:
        """Get entity by ID or None if not found.

        Convenience method equivalent to get(id, raise_on_missing=False).

        Args:
            id: Entity identifier.

        Returns:
            ResponseDTO or None if not found.
        """
        return await self.get(id, raise_on_missing=False)

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> PaginatedResponse[ResponseDTO]:
        """Get paginated list of entities.

        Args:
            page: Page number (1-indexed).
            size: Items per page.
            filters: Optional filter criteria.
            sort_by: Field to sort by.
            sort_order: Sort order ("asc" or "desc").

        Returns:
            PaginatedResponse: Paginated list of entities.
        """
        skip = (page - 1) * size
        entities, total = await self._repository.get_all(
            skip=skip,
            limit=size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = self._mapper.to_dto_list(entities)
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
        )

    async def create(self, data: CreateDTO) -> ResponseDTO:
        """Create new entity.

        Args:
            data: Entity creation data.

        Returns:
            ResponseDTO: Created entity as response DTO.

        Raises:
            ValidationError: If validation fails.
        """
        self._validate_create(data)
        entity = await self._repository.create(data)
        return self._mapper.to_dto(entity)

    async def update(self, id: str, data: UpdateDTO) -> ResponseDTO:
        """Update existing entity.

        Args:
            id: Entity identifier.
            data: Update data.

        Returns:
            ResponseDTO: Updated entity as response DTO.

        Raises:
            EntityNotFoundError: If entity not found.
            ValidationError: If validation fails.
        """
        self._validate_update(data)
        entity = await self._repository.update(id, data)
        if entity is None:
            raise EntityNotFoundError(self._entity_name, id)
        return self._mapper.to_dto(entity)

    async def delete(self, id: str) -> bool:
        """Delete entity.

        Args:
            id: Entity identifier.

        Returns:
            bool: True if deleted.

        Raises:
            EntityNotFoundError: If entity not found.
        """
        deleted = await self._repository.delete(id)
        if not deleted:
            raise EntityNotFoundError(self._entity_name, id)
        return True

    async def exists(self, id: str) -> bool:
        """Check if entity exists.

        Args:
            id: Entity identifier.

        Returns:
            bool: True if entity exists.
        """
        return await self._repository.exists(id)

    async def create_many(self, data: Sequence[CreateDTO]) -> "list[ResponseDTO]":
        """Bulk create entities.

        Args:
            data: List of entity creation data.

        Returns:
            list[ResponseDTO]: List of created entities as response DTOs.

        Raises:
            ValidationError: If validation fails for any item.
        """
        for item in data:
            self._validate_create(item)
        entities = await self._repository.create_many(data)
        return self._mapper.to_dto_list(entities)

    def _validate_create(self, data: CreateDTO) -> None:
        """Validate creation data.

        Override in subclasses to add custom validation.

        Args:
            data: Creation data to validate.

        Raises:
            ValidationError: If validation fails.
        """
        pass

    def _validate_update(self, data: UpdateDTO) -> None:
        """Validate update data.

        Override in subclasses to add custom validation.

        Args:
            data: Update data to validate.

        Raises:
            ValidationError: If validation fails.
        """
        pass
