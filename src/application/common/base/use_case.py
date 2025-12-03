"""Generic Use Case base class for application layer.

Provides CRUD operations with Unit of Work support.
Uses PEP 695 type parameter syntax.

**Feature: application-layer-improvements-2025**
**Validates: Requirements 4.1, 4.2, 4.3**
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, overload

from application.common.base.dto import PaginatedResponse
from core.base.patterns.result import Result, Ok, Err

logger = logging.getLogger(__name__)


class UseCaseError(Exception):
    """Base exception for use case errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(UseCaseError):
    """Entity not found error."""

    def __init__(self, entity_type: str, entity_id: Any) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id '{entity_id}' not found", "NOT_FOUND")


class ValidationError(UseCaseError):
    """Validation error."""

    def __init__(
        self, message: str, errors: list[dict[str, Any]] | None = None
    ) -> None:
        self.errors = errors or []
        super().__init__(message, "VALIDATION_ERROR")


class BaseUseCase[TEntity, TId](ABC):
    """Base use case with CRUD operations.

    Provides standard CRUD operations with Unit of Work support
    and overloaded methods for type-safe error handling.

    Type Parameters:
        TEntity: The entity type this use case operates on.
        TId: The entity ID type.

    Example:
        >>> class UserUseCase(BaseUseCase[User, str]):
        ...     def __init__(self, uow: UnitOfWork, repo: UserRepository):
        ...         self._uow = uow
        ...         self._repo = repo
        ...
        ...     async def _get_repository(self):
        ...         return self._repo
    """

    @abstractmethod
    async def _get_repository(self) -> Any:
        """Get the repository for this use case.

        Returns:
            Repository instance.
        """
        ...

    @abstractmethod
    async def _get_unit_of_work(self) -> Any:
        """Get the unit of work for this use case.

        Returns:
            Unit of Work instance.
        """
        ...

    # Overloaded get method for type-safe returns
    @overload
    async def get(
        self,
        entity_id: TId,
        *,
        raise_on_missing: bool = True,
    ) -> TEntity: ...

    @overload
    async def get(
        self,
        entity_id: TId,
        *,
        raise_on_missing: bool = False,
    ) -> TEntity | None: ...

    async def get(
        self,
        entity_id: TId,
        *,
        raise_on_missing: bool = True,
    ) -> TEntity | None:
        """Get an entity by ID.

        Args:
            entity_id: The entity ID.
            raise_on_missing: If True, raises NotFoundError when not found.

        Returns:
            The entity if found, None if not found and raise_on_missing=False.

        Raises:
            NotFoundError: If entity not found and raise_on_missing=True.
        """
        repo = await self._get_repository()
        entity = await repo.get_by_id(entity_id)

        if entity is None and raise_on_missing:
            raise NotFoundError(self._get_entity_name(), entity_id)

        return entity

    async def get_result(self, entity_id: TId) -> Result[TEntity, UseCaseError]:
        """Get an entity by ID, returning a Result.

        Args:
            entity_id: The entity ID.

        Returns:
            Result containing the entity or error.
        """
        try:
            entity = await self.get(entity_id, raise_on_missing=True)
            return Ok(entity)
        except NotFoundError as e:
            return Err(e)

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> PaginatedResponse[TEntity]:
        """List entities with pagination.

        Args:
            page: Page number (1-indexed).
            size: Items per page.
            filters: Optional filters.
            sort_by: Field to sort by.
            sort_order: Sort direction ('asc' or 'desc').

        Returns:
            Paginated response with entities.
        """
        repo = await self._get_repository()
        skip = (page - 1) * size

        entities, total = await repo.get_all(
            skip=skip,
            limit=size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return PaginatedResponse(
            items=list(entities),
            total=total,
            page=page,
            size=size,
        )

    async def create(self, data: Any) -> Result[TEntity, UseCaseError]:
        """Create a new entity.

        Args:
            data: Creation data (DTO).

        Returns:
            Result containing the created entity or error.
        """
        validation_result = await self._validate_create(data)
        if validation_result.is_err():
            return validation_result

        try:
            uow = await self._get_unit_of_work()
            repo = await self._get_repository()

            async with uow:
                entity = await repo.create(data)
                await uow.commit()
                await self._after_create(entity)
                return Ok(entity)
        except NotFoundError:
            raise
        except ValidationError as e:
            return Err(e)
        except Exception as e:
            logger.exception(
                f"Unexpected error creating {self._get_entity_name()}",
                extra={"entity_type": self._get_entity_name(), "operation": "CREATE"},
            )
            return Err(UseCaseError(str(e), code="INTERNAL_ERROR"))

    async def update(
        self,
        entity_id: TId,
        data: Any,
    ) -> Result[TEntity, UseCaseError]:
        """Update an existing entity.

        Args:
            entity_id: The entity ID.
            data: Update data (DTO).

        Returns:
            Result containing the updated entity or error.
        """
        validation_result = await self._validate_update(entity_id, data)
        if validation_result.is_err():
            return validation_result

        try:
            uow = await self._get_unit_of_work()
            repo = await self._get_repository()

            async with uow:
                entity = await repo.update(entity_id, data)
                if entity is None:
                    return Err(NotFoundError(self._get_entity_name(), entity_id))
                await uow.commit()
                await self._after_update(entity)
                return Ok(entity)
        except NotFoundError:
            raise
        except ValidationError as e:
            return Err(e)
        except Exception as e:
            logger.exception(
                f"Unexpected error updating {self._get_entity_name()} {entity_id}",
                extra={
                    "entity_type": self._get_entity_name(),
                    "entity_id": str(entity_id),
                    "operation": "UPDATE",
                },
            )
            return Err(UseCaseError(str(e), code="INTERNAL_ERROR"))

    async def delete(self, entity_id: TId) -> Result[bool, UseCaseError]:
        """Delete an entity.

        Args:
            entity_id: The entity ID.

        Returns:
            Result containing True if deleted or error.
        """
        try:
            uow = await self._get_unit_of_work()
            repo = await self._get_repository()

            async with uow:
                deleted = await repo.delete(entity_id)
                if not deleted:
                    return Err(NotFoundError(self._get_entity_name(), entity_id))
                await uow.commit()
                await self._after_delete(entity_id)
                return Ok(True)
        except NotFoundError:
            raise
        except Exception as e:
            logger.exception(
                f"Unexpected error deleting {self._get_entity_name()} {entity_id}",
                extra={
                    "entity_type": self._get_entity_name(),
                    "entity_id": str(entity_id),
                    "operation": "DELETE",
                },
            )
            return Err(UseCaseError(str(e), code="INTERNAL_ERROR"))

    # Hooks for customization
    async def _validate_create(self, data: Any) -> Result[None, UseCaseError]:
        """Validate creation data. Override to add custom validation."""
        return Ok(None)

    async def _validate_update(
        self,
        entity_id: TId,
        data: Any,
    ) -> Result[None, UseCaseError]:
        """Validate update data. Override to add custom validation."""
        return Ok(None)

    async def _after_create(self, entity: TEntity) -> None:
        """Hook called after entity creation. Override for side effects."""
        pass

    async def _after_update(self, entity: TEntity) -> None:
        """Hook called after entity update. Override for side effects."""
        pass

    async def _after_delete(self, entity_id: TId) -> None:
        """Hook called after entity deletion. Override for side effects."""
        pass

    def _get_entity_name(self) -> str:
        """Get the entity type name for error messages."""
        return "Entity"
