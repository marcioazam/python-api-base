"""Tenant-aware repository with automatic filtering.

**Feature: enterprise-features-2025**
**Validates: Requirements 7.1, 7.2**
**Split from: service.py for SRP compliance**
"""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.multitenancy.models import get_current_tenant
from core.base.repository import IRepository

logger = logging.getLogger(__name__)


class TenantAware(BaseModel):
    """Mixin for tenant-aware entities.

    Entities inheriting from this will have automatic
    tenant filtering applied.
    """

    tenant_id: str = Field(description="Tenant identifier")


class TenantRepository[T, CreateT: BaseModel, UpdateT: BaseModel](
    IRepository[T, CreateT, UpdateT]
):
    """Repository with automatic tenant filtering.

    All queries are automatically filtered by tenant_id.
    Creates automatically set the tenant_id.

    Type Parameters:
        T: Entity type (must have tenant_id field).
        CreateT: DTO type for creating entities.
        UpdateT: DTO type for updating entities.
    """

    def __init__(
        self,
        session: AsyncSession,
        model_class: type[T],
        tenant_id: str | None = None,
        tenant_field: str = "tenant_id",
    ) -> None:
        """Initialize tenant repository.

        Args:
            session: SQLAlchemy async session.
            model_class: The entity model class.
            tenant_id: Explicit tenant ID (uses context if None).
            tenant_field: Name of the tenant field in the model.
        """
        self._session = session
        self._model_class = model_class
        self._explicit_tenant_id = tenant_id
        self._tenant_field = tenant_field

    @property
    def tenant_id(self) -> str:
        """Get the effective tenant ID."""
        tenant = self._explicit_tenant_id or get_current_tenant()
        if tenant is None:
            raise ValueError("No tenant ID available in context or explicit setting")
        return tenant

    def _apply_tenant_filter(self, query: Any) -> Any:
        """Apply tenant filter to a query."""
        tenant_col = getattr(self._model_class, self._tenant_field, None)
        if tenant_col is not None:
            return query.where(tenant_col == self.tenant_id)
        return query

    async def get_by_id(self, id: str) -> T | None:
        """Get entity by ID within tenant scope."""
        query = select(self._model_class).where(
            self._model_class.id == id  # type: ignore[attr-defined]
        )
        query = self._apply_tenant_filter(query)
        result = await self._session.execute(query)
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
        """Get all entities within tenant scope."""
        query = select(self._model_class)
        query = self._apply_tenant_filter(query)

        if filters:
            for field, value in filters.items():
                if hasattr(self._model_class, field):
                    query = query.where(getattr(self._model_class, field) == value)

        if hasattr(self._model_class, "is_deleted"):
            query = query.where(self._model_class.is_deleted.is_(False))

        # Count query
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply sorting
        if sort_by and hasattr(self._model_class, sort_by):
            order_col = getattr(self._model_class, sort_by)
            query = query.order_by(
                order_col.desc() if sort_order == "desc" else order_col
            )

        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self._session.execute(query)

        return list(result.scalars().all()), total

    async def create(self, data: CreateT) -> T:
        """Create entity with automatic tenant assignment."""
        entity_data = data.model_dump()
        entity_data[self._tenant_field] = self.tenant_id
        entity = self._model_class(**entity_data)
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, id: str, data: UpdateT) -> T | None:
        """Update entity within tenant scope."""
        entity = await self.get_by_id(id)
        if entity is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        if hasattr(entity, "updated_at"):
            entity.updated_at = datetime.now(tz=UTC)

        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, id: str, *, soft: bool = True) -> bool:
        """Delete entity within tenant scope."""
        entity = await self.get_by_id(id)
        if entity is None:
            return False

        if soft and hasattr(entity, "is_deleted"):
            entity.is_deleted = True
            if hasattr(entity, "updated_at"):
                entity.updated_at = datetime.now(tz=UTC)
            await self._session.flush()
            logger.info(
                f"Soft deleted {self._model_class.__name__} {id} for tenant {self.tenant_id}"
            )
        else:
            logger.warning(
                f"Hard delete: {self._model_class.__name__} {id} for tenant {self.tenant_id}",
                extra={
                    "entity_type": self._model_class.__name__,
                    "entity_id": id,
                    "tenant_id": self.tenant_id,
                    "operation": "HARD_DELETE",
                },
            )
            await self._session.delete(entity)
            await self._session.flush()

        return True

    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]:
        """Bulk create entities with tenant assignment."""
        entities = []
        for item in data:
            entity_data = item.model_dump()
            entity_data[self._tenant_field] = self.tenant_id
            entity = self._model_class(**entity_data)
            self._session.add(entity)
            entities.append(entity)

        await self._session.flush()
        for entity in entities:
            await self._session.refresh(entity)

        return entities

    async def exists(self, id: str) -> bool:
        """Check if entity exists within tenant scope."""
        entity = await self.get_by_id(id)
        return entity is not None

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities within tenant scope."""
        _, total = await self.get_all(skip=0, limit=1, filters=filters)
        return total
