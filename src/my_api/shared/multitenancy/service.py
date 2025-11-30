"""multitenancy service."""

from collections.abc import Sequence
from contextvars import ContextVar
from datetime import datetime, UTC
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from my_api.shared.repository import IRepository
from .models import TenantContext

# Context variable for current tenant
_current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


class TenantAware(BaseModel):
    """Mixin for tenant-aware entities.

    Entities inheriting from this will have automatic
    tenant filtering applied.
    """

    tenant_id: str = Field(description="Tenant identifier")

class TenantRepository[T, CreateT: BaseModel, UpdateT: BaseModel](IRepository[T, CreateT, UpdateT]):
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
        """Get the effective tenant ID.

        Returns:
            The tenant ID from explicit setting or context.

        Raises:
            ValueError: If no tenant ID is available.
        """
        tenant = self._explicit_tenant_id or get_current_tenant()
        if tenant is None:
            raise ValueError("No tenant ID available in context or explicit setting")
        return tenant

    def _apply_tenant_filter(self, query: Any) -> Any:
        """Apply tenant filter to a query.

        Args:
            query: SQLAlchemy query to filter.

        Returns:
            Filtered query.
        """
        tenant_col = getattr(self._model_class, self._tenant_field, None)
        if tenant_col is not None:
            return query.where(tenant_col == self.tenant_id)
        return query

    async def get_by_id(self, id: str) -> T | None:
        """Get entity by ID within tenant scope.

        Args:
            id: Entity identifier.

        Returns:
            Entity if found within tenant, None otherwise.
        """
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
        """Get all entities within tenant scope.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.
            filters: Additional filter criteria.
            sort_by: Field to sort by.
            sort_order: Sort order ("asc" or "desc").

        Returns:
            Tuple of (entities, total_count).
        """
        # Base query with tenant filter
        query = select(self._model_class)
        query = self._apply_tenant_filter(query)

        # Apply additional filters
        if filters:
            for field, value in filters.items():
                if hasattr(self._model_class, field):
                    query = query.where(
                        getattr(self._model_class, field) == value
                    )

        # Apply soft delete filter if exists
        if hasattr(self._model_class, "is_deleted"):
            query = query.where(
                self._model_class.is_deleted.is_(False)
            )

        # Count total
        count_result = await self._session.execute(query)
        total = len(count_result.scalars().all())

        # Apply sorting
        if sort_by and hasattr(self._model_class, sort_by):
            order_col = getattr(self._model_class, sort_by)
            if sort_order.lower() == "desc":
                order_col = order_col.desc()
            query = query.order_by(order_col)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self._session.execute(query)
        entities = result.scalars().all()

        return list(entities), total

    async def create(self, data: CreateT) -> T:
        """Create entity with automatic tenant assignment.

        Args:
            data: Creation data.

        Returns:
            Created entity with tenant_id set.
        """
        # Convert to dict and add tenant_id
        entity_data = data.model_dump()
        entity_data[self._tenant_field] = self.tenant_id

        entity = self._model_class(**entity_data)
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)

        return entity

    async def update(self, id: str, data: UpdateT) -> T | None:
        """Update entity within tenant scope.

        Args:
            id: Entity identifier.
            data: Update data.

        Returns:
            Updated entity if found, None otherwise.
        """
        entity = await self.get_by_id(id)
        if entity is None:
            return None

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        # Update timestamp if exists
        if hasattr(entity, "updated_at"):
            setattr(entity, "updated_at", datetime.now(tz=UTC))

        await self._session.flush()
        await self._session.refresh(entity)

        return entity

    async def delete(self, id: str, *, soft: bool = True) -> bool:
        """Delete entity within tenant scope.

        Args:
            id: Entity identifier.
            soft: If True, soft delete; otherwise hard delete.

        Returns:
            True if deleted, False if not found.
        """
        entity = await self.get_by_id(id)
        if entity is None:
            return False

        if soft and hasattr(entity, "is_deleted"):
            setattr(entity, "is_deleted", True)
            if hasattr(entity, "updated_at"):
                setattr(entity, "updated_at", datetime.now(tz=UTC))
            await self._session.flush()
        else:
            await self._session.delete(entity)
            await self._session.flush()

        return True

    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]:
        """Bulk create entities with tenant assignment.

        Args:
            data: List of creation data.

        Returns:
            List of created entities.
        """
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
        """Check if entity exists within tenant scope.

        Args:
            id: Entity identifier.

        Returns:
            True if exists, False otherwise.
        """
        entity = await self.get_by_id(id)
        return entity is not None

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities within tenant scope.

        Args:
            filters: Optional filter criteria.

        Returns:
            Count of matching entities.
        """
        _, total = await self.get_all(skip=0, limit=1, filters=filters)
        return total

class TenantMiddleware:
    """ASGI middleware for tenant context extraction.

    Extracts tenant ID from request headers or path and sets
    it in the context for downstream use.

    Usage:
        app.add_middleware(
            TenantMiddleware,
            header_name="X-Tenant-ID",
        )
    """

    def __init__(
        self,
        app: Any,
        header_name: str = "X-Tenant-ID",
        path_param: str | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            app: ASGI application.
            header_name: Header name for tenant ID.
            path_param: Optional path parameter name for tenant ID.
        """
        self.app = app
        self.header_name = header_name.lower()
        self.path_param = path_param

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """Process request and set tenant context."""
        if scope["type"] == "http":
            tenant_id = self._extract_tenant_id(scope)
            if tenant_id:
                async with TenantContext(tenant_id):
                    await self.app(scope, receive, send)
                return

        await self.app(scope, receive, send)

    def _extract_tenant_id(self, scope: dict) -> str | None:
        """Extract tenant ID from request.

        Args:
            scope: ASGI scope.

        Returns:
            Tenant ID if found, None otherwise.
        """
        # Try header first
        headers = dict(scope.get("headers", []))
        header_value = headers.get(self.header_name.encode())
        if header_value:
            return header_value.decode()

        # Try path parameter
        if self.path_param:
            path_params = scope.get("path_params", {})
            if self.path_param in path_params:
                return str(path_params[self.path_param])

        return None

def get_current_tenant() -> str | None:
    """Get the current tenant ID from context.

    Returns:
        The current tenant ID or None if not set.
    """
    return _current_tenant.get()

def set_current_tenant(tenant_id: str | None) -> None:
    """Set the current tenant ID in context.

    Args:
        tenant_id: The tenant ID to set.
    """
    _current_tenant.set(tenant_id)

def require_tenant(func: Any) -> Any:
    """Decorator to require tenant context.

    Raises ValueError if no tenant is set in context.

    Usage:
        @require_tenant
        async def get_items():
            tenant = get_current_tenant()
            # tenant is guaranteed to be set
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if get_current_tenant() is None:
            raise ValueError("Tenant context required but not set")
        return await func(*args, **kwargs)

    return wrapper
