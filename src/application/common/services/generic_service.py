"""Generic service base class with CRUD operations.

**Feature: python-api-base-2025-validation**
**Validates: Requirements 22.1, 22.2, 22.3, 22.4**

Provides a reusable service layer with:
- CRUD operations returning Result pattern
- Validation hooks (pre/post create, update, delete)
- Event publishing integration
- Mapper integration for DTO conversion
- Full compatibility with GenericCRUDRouter
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel

from core.base.patterns.result import Err, Ok, Result
from core.base.repository.interface import IRepository

if TYPE_CHECKING:
    from application.common.mappers.interfaces.mapper_interface import IMapper


logger = logging.getLogger(__name__)


# =============================================================================
# Error Types
# =============================================================================


class ServiceError(Exception):
    """Base error for service operations."""

    def __init__(
        self,
        message: str,
        code: str = "SERVICE_ERROR",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(ServiceError):
    """Entity not found error."""

    status_code: int = 404

    def __init__(self, entity_type: str, entity_id: Any) -> None:
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            code="NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class ValidationError(ServiceError):
    """Validation error."""

    status_code: int = 400

    def __init__(
        self,
        message: str,
        field: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
        )
        self.field = field


class ConflictError(ServiceError):
    """Conflict error (e.g., duplicate entry)."""

    status_code: int = 409

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="CONFLICT", details=details)


# =============================================================================
# Protocols
# =============================================================================


@runtime_checkable
class IEventBus(Protocol):
    """Protocol for event bus integration."""

    async def publish(self, event: dict[str, Any]) -> None:
        """Publish an event."""
        ...


@runtime_checkable
class IServiceMapper[TEntity, TResponse](Protocol):
    """Protocol for service mapper."""

    def to_dto(self, entity: TEntity) -> TResponse:
        """Convert entity to response DTO."""
        ...


# =============================================================================
# Generic Service
# =============================================================================


class GenericService[
    TEntity: BaseModel,
    TCreate: BaseModel,
    TUpdate: BaseModel,
    TResponse: BaseModel,
](ABC):
    """Generic service with CRUD operations and Result pattern.

    Provides a base implementation for service layer operations with:
    - Type-safe CRUD operations
    - Result pattern for error handling
    - Validation hooks for customization
    - Event publishing support
    - Full compatibility with GenericCRUDRouter

    Type Parameters:
        TEntity: Domain entity type.
        TCreate: DTO for creating entities.
        TUpdate: DTO for updating entities.
        TResponse: DTO for response/output.

    Example:
        >>> class UserService(GenericService[User, CreateUserDTO, UpdateUserDTO, UserResponse]):
        ...     entity_name = "User"
        ...
        ...     def __init__(self, repository: IRepository, mapper: IMapper):
        ...         super().__init__(repository, mapper)
        ...
        ...     async def _pre_create(self, data: CreateUserDTO) -> Result[CreateUserDTO, ServiceError]:
        ...         if len(data.password) < 8:
        ...             return Err(ValidationError("Password too short", "password"))
        ...         return Ok(data)

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 22.1, 22.2, 22.3, 22.4**
    """

    # Subclasses MUST override this
    entity_name: str = "Entity"

    def __init__(
        self,
        repository: IRepository[TEntity, TCreate, TUpdate, Any],
        mapper: IServiceMapper[TEntity, TResponse] | None = None,
        event_bus: IEventBus | None = None,
    ) -> None:
        """Initialize generic service.

        Args:
            repository: Repository for data access.
            mapper: Optional mapper for entity-to-DTO conversion.
            event_bus: Optional event bus for publishing domain events.
        """
        self._repository = repository
        self._mapper = mapper
        self._event_bus = event_bus
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # =========================================================================
    # Router-Compatible Interface (list, get, create, update, delete)
    # =========================================================================

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "asc",
        filters: dict[str, Any] | None = None,
    ) -> tuple[Sequence[TResponse], int]:
        """List entities with pagination (router-compatible).

        Args:
            page: Page number (1-indexed).
            size: Items per page.
            sort_by: Field to sort by.
            sort_order: Sort order ("asc" or "desc").
            filters: Optional filter criteria.

        Returns:
            Tuple of (entities, total_count).

        Raises:
            ServiceError: If operation fails.
        """
        skip = (page - 1) * size
        result = await self.get_all(
            skip=skip,
            limit=size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        if result.is_err():
            error = result.error  # type: ignore[union-attr]
            self._logger.error("List failed: %s", error.message)
            raise error
        return result.unwrap()

    async def get(self, entity_id: Any) -> TResponse:
        """Get entity by ID (router-compatible).

        Args:
            entity_id: Entity identifier.

        Returns:
            Entity response DTO.

        Raises:
            NotFoundError: If entity not found.
            ServiceError: If operation fails.
        """
        result = await self.get_by_id(entity_id)
        if result.is_err():
            error = result.error  # type: ignore[union-attr]
            self._logger.error("Get failed for %s: %s", entity_id, error.message)
            raise error
        entity = result.unwrap()
        if entity is None:
            raise NotFoundError(self.entity_name, entity_id)
        return entity

    # =========================================================================
    # CRUD Operations (Result Pattern)
    # =========================================================================

    async def create(self, data: TCreate) -> TResponse:
        """Create a new entity (router-compatible).

        Args:
            data: Creation data.

        Returns:
            Created entity response.

        Raises:
            ValidationError: If validation fails.
            ServiceError: If operation fails.
        """
        result = await self.create_with_result(data)
        if result.is_err():
            error = result.error  # type: ignore[union-attr]
            self._logger.error("Create failed: %s", error.message)
            raise error
        return result.unwrap()

    async def create_with_result(
        self, data: TCreate
    ) -> Result[TResponse, ServiceError]:
        """Create a new entity with Result pattern.

        Args:
            data: Creation data.

        Returns:
            Result containing the created entity response or error.
        """
        self._logger.debug("Creating %s", self.entity_name)

        # Pre-create hook
        pre_result = await self._pre_create(data)
        if pre_result.is_err():
            return Err(pre_result.error)  # type: ignore[union-attr]

        validated_data = pre_result.unwrap()

        try:
            entity = await self._repository.create(validated_data)
        except Exception as e:
            self._logger.exception("Failed to create %s", self.entity_name)
            return Err(ServiceError(f"Failed to create {self.entity_name}: {e}"))

        # Post-create hook
        await self._post_create(entity)

        # Publish event
        await self._safe_publish_event("Created", entity)

        response = self._to_response(entity)
        self._logger.info("Created %s with id %s", self.entity_name, getattr(entity, "id", "unknown"))
        return Ok(response)

    async def update(self, entity_id: Any, data: TUpdate) -> TResponse:
        """Update an existing entity (router-compatible).

        Args:
            entity_id: ID of entity to update.
            data: Update data.

        Returns:
            Updated entity response.

        Raises:
            NotFoundError: If entity not found.
            ValidationError: If validation fails.
            ServiceError: If operation fails.
        """
        result = await self.update_with_result(entity_id, data)
        if result.is_err():
            error = result.error  # type: ignore[union-attr]
            self._logger.error("Update failed for %s: %s", entity_id, error.message)
            raise error
        return result.unwrap()

    async def update_with_result(
        self, entity_id: Any, data: TUpdate
    ) -> Result[TResponse, ServiceError]:
        """Update an existing entity with Result pattern.

        Args:
            entity_id: ID of entity to update.
            data: Update data.

        Returns:
            Result containing the updated entity response or error.
        """
        self._logger.debug("Updating %s %s", self.entity_name, entity_id)

        # Check entity exists
        existing = await self._repository.get_by_id(entity_id)
        if existing is None:
            return Err(NotFoundError(self.entity_name, entity_id))

        # Pre-update hook
        pre_result = await self._pre_update(entity_id, data, existing)
        if pre_result.is_err():
            return Err(pre_result.error)  # type: ignore[union-attr]

        validated_data = pre_result.unwrap()

        try:
            updated = await self._repository.update(entity_id, validated_data)
            if updated is None:
                return Err(NotFoundError(self.entity_name, entity_id))
        except Exception as e:
            self._logger.exception("Failed to update %s %s", self.entity_name, entity_id)
            return Err(ServiceError(f"Failed to update {self.entity_name}: {e}"))

        # Post-update hook
        await self._post_update(updated, existing)

        # Publish event
        await self._safe_publish_event("Updated", updated)

        response = self._to_response(updated)
        self._logger.info("Updated %s %s", self.entity_name, entity_id)
        return Ok(response)

    async def delete(self, entity_id: Any, *, soft: bool = True) -> bool:
        """Delete an entity (router-compatible).

        Args:
            entity_id: ID of entity to delete.
            soft: If True, perform soft delete. Default True.

        Returns:
            True if deleted.

        Raises:
            NotFoundError: If entity not found.
            ServiceError: If operation fails.
        """
        result = await self.delete_with_result(entity_id, soft=soft)
        if result.is_err():
            error = result.error  # type: ignore[union-attr]
            self._logger.error("Delete failed for %s: %s", entity_id, error.message)
            raise error
        return result.unwrap()

    async def delete_with_result(
        self, entity_id: Any, *, soft: bool = True
    ) -> Result[bool, ServiceError]:
        """Delete an entity with Result pattern.

        Args:
            entity_id: ID of entity to delete.
            soft: If True, perform soft delete. Default True.

        Returns:
            Result containing True if deleted, or error.
        """
        self._logger.debug("Deleting %s %s (soft=%s)", self.entity_name, entity_id, soft)

        # Check entity exists
        existing = await self._repository.get_by_id(entity_id)
        if existing is None:
            return Err(NotFoundError(self.entity_name, entity_id))

        # Pre-delete hook
        pre_result = await self._pre_delete(entity_id, existing)
        if pre_result.is_err():
            return Err(pre_result.error)  # type: ignore[union-attr]

        try:
            deleted = await self._repository.delete(entity_id, soft=soft)
            if not deleted:
                return Err(ServiceError(f"Failed to delete {self.entity_name}"))
        except Exception as e:
            self._logger.exception("Failed to delete %s %s", self.entity_name, entity_id)
            return Err(ServiceError(f"Failed to delete {self.entity_name}: {e}"))

        # Post-delete hook
        await self._post_delete(existing)

        # Publish event
        await self._safe_publish_event("Deleted", existing)

        self._logger.info("Deleted %s %s", self.entity_name, entity_id)
        return Ok(True)

    async def get_by_id(
        self, entity_id: Any
    ) -> Result[TResponse | None, ServiceError]:
        """Get entity by ID with Result pattern.

        Args:
            entity_id: Entity identifier.

        Returns:
            Result containing entity response or None if not found.
        """
        try:
            entity = await self._repository.get_by_id(entity_id)
        except Exception as e:
            self._logger.exception("Failed to get %s %s", self.entity_name, entity_id)
            return Err(ServiceError(f"Failed to get {self.entity_name}: {e}"))

        if entity is None:
            return Ok(None)

        response = self._to_response(entity)
        return Ok(response)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> Result[tuple[Sequence[TResponse], int], ServiceError]:
        """Get paginated list of entities with Result pattern.

        Args:
            skip: Number of items to skip.
            limit: Maximum items to return.
            filters: Optional filter criteria.
            sort_by: Field to sort by.
            sort_order: Sort order ("asc" or "desc").

        Returns:
            Result containing tuple of (entities, total_count).
        """
        try:
            entities, total = await self._repository.get_all(
                skip=skip,
                limit=limit,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        except Exception as e:
            self._logger.exception("Failed to list %s", self.entity_name)
            return Err(ServiceError(f"Failed to list {self.entity_name}: {e}"))

        responses = [self._to_response(e) for e in entities]
        return Ok((responses, total))

    async def create_many(self, data: Sequence[TCreate]) -> Sequence[TResponse]:
        """Bulk create entities (router-compatible).

        Args:
            data: List of creation data.

        Returns:
            List of created entity responses.

        Raises:
            ServiceError: If operation fails.
        """
        self._logger.debug("Bulk creating %d %s", len(data), self.entity_name)

        try:
            entities = await self._repository.create_many(data)
        except Exception as e:
            self._logger.exception("Failed to bulk create %s", self.entity_name)
            raise ServiceError(f"Failed to bulk create {self.entity_name}: {e}") from e

        responses = [self._to_response(e) for e in entities]
        self._logger.info("Bulk created %d %s", len(responses), self.entity_name)
        return responses

    async def exists(self, entity_id: Any) -> bool:
        """Check if entity exists.

        Args:
            entity_id: Entity identifier.

        Returns:
            True if entity exists.
        """
        return await self._repository.exists(entity_id)

    # =========================================================================
    # Validation Hooks (Override in subclasses)
    # =========================================================================

    async def _pre_create(self, data: TCreate) -> Result[TCreate, ServiceError]:
        """Hook called before creating an entity.

        Override to add custom validation or transformation.

        Args:
            data: Creation data.

        Returns:
            Result with validated/transformed data or error.
        """
        return Ok(data)

    async def _post_create(self, entity: TEntity) -> None:
        """Hook called after creating an entity.

        Override to add custom post-creation logic.

        Args:
            entity: Created entity.
        """

    async def _pre_update(
        self, entity_id: Any, data: TUpdate, existing: TEntity
    ) -> Result[TUpdate, ServiceError]:
        """Hook called before updating an entity.

        Override to add custom validation or transformation.

        Args:
            entity_id: Entity ID.
            data: Update data.
            existing: Existing entity.

        Returns:
            Result with validated/transformed data or error.
        """
        return Ok(data)

    async def _post_update(self, updated: TEntity, previous: TEntity) -> None:
        """Hook called after updating an entity.

        Override to add custom post-update logic.

        Args:
            updated: Updated entity.
            previous: Previous entity state.
        """

    async def _pre_delete(
        self, entity_id: Any, existing: TEntity
    ) -> Result[None, ServiceError]:
        """Hook called before deleting an entity.

        Override to add custom validation.

        Args:
            entity_id: Entity ID.
            existing: Existing entity.

        Returns:
            Result with None or error.
        """
        return Ok(None)

    async def _post_delete(self, deleted: TEntity) -> None:
        """Hook called after deleting an entity.

        Override to add custom post-deletion logic.

        Args:
            deleted: Deleted entity.
        """

    # =========================================================================
    # Event Publishing
    # =========================================================================

    async def _safe_publish_event(self, event_type: str, entity: TEntity) -> None:
        """Safely publish an event, logging errors without raising.

        Args:
            event_type: Type of event (Created, Updated, Deleted).
            entity: Entity involved in the event.
        """
        if self._event_bus is None:
            return

        try:
            event = {
                "type": f"{self.entity_name}{event_type}",
                "entity_id": str(getattr(entity, "id", None)),
                "entity_type": self.entity_name,
            }
            await self._event_bus.publish(event)
        except Exception:
            self._logger.exception(
                "Failed to publish %s%s event", self.entity_name, event_type
            )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _to_response(self, entity: TEntity) -> TResponse:
        """Convert entity to response DTO.

        Uses mapper if available, otherwise returns entity as-is.

        Args:
            entity: Entity to convert.

        Returns:
            Response DTO.
        """
        if self._mapper is not None:
            return self._mapper.to_dto(entity)
        # Type assertion: entity must be compatible with TResponse
        return entity  # type: ignore[return-value]
