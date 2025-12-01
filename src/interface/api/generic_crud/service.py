"""Generic Service Layer with business logic abstraction."""

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from .repository import FilterCondition, GenericRepository, PaginatedResult, QueryOptions, SortCondition


@dataclass
class ServiceResult[T]:
    """Service operation result."""

    success: bool
    data: T | None = None
    error: str | None = None
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationRule:
    """Custom validation rule."""

    field: str
    validator: Callable[[Any], bool]
    message: str
    async_validator: Callable[[Any], Awaitable[bool]] | None = None


class GenericService[T, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel, ResponseSchemaType: BaseModel]:
    """Generic service base class with business logic."""

    def __init__(self, repository: GenericRepository[T], response_model: type[ResponseSchemaType]) -> None:
        self._repository = repository
        self._response_model = response_model
        self._logger = logging.getLogger(self.__class__.__name__)
        self._validation_rules: list[ValidationRule] = []
        self._hooks: dict[str, list[Callable]] = {
            "before_create": [],
            "after_create": [],
            "before_update": [],
            "after_update": [],
            "before_delete": [],
            "after_delete": [],
        }

    @property
    def repository(self) -> GenericRepository[T]:
        return self._repository

    def add_validation_rule(self, rule: ValidationRule) -> None:
        """Add custom validation rule."""
        self._validation_rules.append(rule)

    def add_hook(self, event: str, callback: Callable) -> None:
        """Add event hook."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    async def _run_hooks(self, event: str, data: Any) -> None:
        """Run event hooks."""
        for hook in self._hooks.get(event, []):
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(data)
                else:
                    hook(data)
            except Exception as e:
                self._logger.error(f"Hook {event} failed: {e}")

    async def _validate_data(self, data: Any, rules: list[ValidationRule]) -> list[str]:
        """Validate data against custom rules."""
        errors = []
        for rule in rules:
            try:
                field_value = getattr(data, rule.field, None)
                is_valid = await rule.async_validator(field_value) if rule.async_validator else rule.validator(field_value)
                if not is_valid:
                    errors.append(rule.message)
            except Exception as e:
                errors.append(f"Validation error for {rule.field}: {e}")
        return errors

    def _to_response_model(self, obj: T) -> ResponseSchemaType:
        """Convert domain object to response model."""
        data = obj.__dict__ if hasattr(obj, "__dict__") else dict(obj)
        return self._response_model(**data)

    async def create(self, obj_in: CreateSchemaType) -> ServiceResult[ResponseSchemaType]:
        """Create a new record with validation and hooks."""
        try:
            validation_errors = await self._validate_data(obj_in, self._validation_rules)
            if validation_errors:
                return ServiceResult(success=False, errors=validation_errors)

            await self._run_hooks("before_create", obj_in)
            db_obj = await self._repository.create(obj_in)
            await self._run_hooks("after_create", db_obj)

            response_obj = self._to_response_model(db_obj)
            self._logger.info(f"Created {self._repository.model.__name__} with ID: {db_obj.id}")
            return ServiceResult(success=True, data=response_obj)
        except ValidationError as e:
            return ServiceResult(success=False, error="Validation failed", errors=[str(err) for err in e.errors()])
        except Exception as e:
            self._logger.error(f"Create failed: {e}")
            return ServiceResult(success=False, error=str(e))

    async def get(self, id: Any, include_relations: list[str] | None = None) -> ServiceResult[ResponseSchemaType]:
        """Get a record by ID."""
        try:
            options = QueryOptions(include_relations=include_relations or [])
            db_obj = await self._repository.get(id, options)
            if not db_obj:
                return ServiceResult(success=False, error=f"Record with ID {id} not found")
            return ServiceResult(success=True, data=self._to_response_model(db_obj))
        except Exception as e:
            self._logger.error(f"Get failed: {e}")
            return ServiceResult(success=False, error=str(e))

    async def get_multi(
        self,
        filters: list[FilterCondition] | None = None,
        sorts: list[SortCondition] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        include_relations: list[str] | None = None,
    ) -> ServiceResult[list[ResponseSchemaType]]:
        """Get multiple records with filtering and sorting."""
        try:
            options = QueryOptions(
                filters=filters or [],
                sorts=sorts or [],
                limit=limit,
                offset=offset,
                include_relations=include_relations or [],
            )
            db_objs = await self._repository.get_multi(options)
            response_objs = [self._to_response_model(obj) for obj in db_objs]
            return ServiceResult(success=True, data=response_objs, metadata={"count": len(response_objs)})
        except Exception as e:
            self._logger.error(f"Get multi failed: {e}")
            return ServiceResult(success=False, error=str(e))

    async def get_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        filters: list[FilterCondition] | None = None,
        sorts: list[SortCondition] | None = None,
        include_relations: list[str] | None = None,
    ) -> ServiceResult[PaginatedResult[ResponseSchemaType]]:
        """Get paginated records."""
        try:
            options = QueryOptions(filters=filters or [], sorts=sorts or [], include_relations=include_relations or [])
            paginated = await self._repository.get_paginated(page, per_page, options)
            response_items = [self._to_response_model(obj) for obj in paginated.items]
            response_paginated = PaginatedResult(
                items=response_items,
                total=paginated.total,
                page=paginated.page,
                per_page=paginated.per_page,
                has_next=paginated.has_next,
                has_prev=paginated.has_prev,
            )
            return ServiceResult(success=True, data=response_paginated)
        except Exception as e:
            self._logger.error(f"Get paginated failed: {e}")
            return ServiceResult(success=False, error=str(e))

    async def update(self, id: Any, obj_in: UpdateSchemaType) -> ServiceResult[ResponseSchemaType]:
        """Update a record with validation and hooks."""
        try:
            existing = await self._repository.get(id)
            if not existing:
                return ServiceResult(success=False, error=f"Record with ID {id} not found")

            validation_errors = await self._validate_data(obj_in, self._validation_rules)
            if validation_errors:
                return ServiceResult(success=False, errors=validation_errors)

            await self._run_hooks("before_update", {"id": id, "data": obj_in, "existing": existing})
            db_obj = await self._repository.update(id, obj_in)
            await self._run_hooks("after_update", db_obj)

            response_obj = self._to_response_model(db_obj)
            self._logger.info(f"Updated {self._repository.model.__name__} with ID: {id}")
            return ServiceResult(success=True, data=response_obj)
        except ValidationError as e:
            return ServiceResult(success=False, error="Validation failed", errors=[str(err) for err in e.errors()])
        except Exception as e:
            self._logger.error(f"Update failed: {e}")
            return ServiceResult(success=False, error=str(e))

    async def delete(self, id: Any) -> ServiceResult[bool]:
        """Delete a record with hooks."""
        try:
            existing = await self._repository.get(id)
            if not existing:
                return ServiceResult(success=False, error=f"Record with ID {id} not found")

            await self._run_hooks("before_delete", existing)
            deleted = await self._repository.delete(id)
            if deleted:
                await self._run_hooks("after_delete", {"id": id, "deleted_obj": existing})
                self._logger.info(f"Deleted {self._repository.model.__name__} with ID: {id}")
                return ServiceResult(success=True, data=True)
            return ServiceResult(success=False, error="Delete operation failed")
        except Exception as e:
            self._logger.error(f"Delete failed: {e}")
            return ServiceResult(success=False, error=str(e))

    async def bulk_create(self, objs_in: list[CreateSchemaType]) -> ServiceResult[list[ResponseSchemaType]]:
        """Bulk create records."""
        try:
            all_errors = []
            for i, obj_in in enumerate(objs_in):
                validation_errors = await self._validate_data(obj_in, self._validation_rules)
                if validation_errors:
                    all_errors.extend([f"Object {i}: {err}" for err in validation_errors])

            if all_errors:
                return ServiceResult(success=False, errors=all_errors)

            db_objs = await self._repository.bulk_create(objs_in)
            response_objs = [self._to_response_model(obj) for obj in db_objs]
            self._logger.info(f"Bulk created {len(db_objs)} {self._repository.model.__name__} records")
            return ServiceResult(success=True, data=response_objs, metadata={"created_count": len(db_objs)})
        except Exception as e:
            self._logger.error(f"Bulk create failed: {e}")
            return ServiceResult(success=False, error=str(e))

    async def count(self, filters: list[FilterCondition] | None = None) -> ServiceResult[int]:
        """Count records matching criteria."""
        try:
            options = QueryOptions(filters=filters or [])
            count = await self._repository.count(options)
            return ServiceResult(success=True, data=count)
        except Exception as e:
            self._logger.error(f"Count failed: {e}")
            return ServiceResult(success=False, error=str(e))

    async def exists(self, id: Any) -> ServiceResult[bool]:
        """Check if record exists."""
        try:
            exists = await self._repository.exists(id)
            return ServiceResult(success=True, data=exists)
        except Exception as e:
            self._logger.error(f"Exists check failed: {e}")
            return ServiceResult(success=False, error=str(e))
