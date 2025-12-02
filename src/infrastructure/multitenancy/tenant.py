"""Generic multitenancy support with PEP 695 type parameters.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5**
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class TenantResolutionStrategy(Enum):
    """Tenant resolution strategies."""

    HEADER = "header"
    SUBDOMAIN = "subdomain"
    PATH = "path"
    JWT_CLAIM = "jwt_claim"
    QUERY_PARAM = "query_param"


@dataclass(frozen=True, slots=True)
class TenantInfo[TId]:
    """Tenant information with typed ID.

    Type Parameters:
        TId: The type of tenant identifier.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 18.1**
    """

    id: TId
    name: str
    schema_name: str | None = None
    settings: dict[str, Any] | None = None
    is_active: bool = True


# Context variable for current tenant
_current_tenant: ContextVar[TenantInfo[Any] | None] = ContextVar(
    "current_tenant", default=None
)


class TenantContext[TId]:
    """Generic tenant context with configurable resolution.

    Type Parameters:
        TId: The type of tenant identifier.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 18.1**
    """

    def __init__(
        self,
        strategy: TenantResolutionStrategy = TenantResolutionStrategy.HEADER,
        header_name: str = "X-Tenant-ID",
        jwt_claim: str = "tenant_id",
        query_param: str = "tenant_id",
    ) -> None:
        self._strategy = strategy
        self._header_name = header_name
        self._jwt_claim = jwt_claim
        self._query_param = query_param

    @staticmethod
    def get_current() -> TenantInfo[Any] | None:
        """Get current tenant from context."""
        return _current_tenant.get()

    @staticmethod
    def set_current(tenant: TenantInfo[Any] | None) -> None:
        """Set current tenant in context."""
        _current_tenant.set(tenant)

    def resolve_from_headers(self, headers: dict[str, str]) -> TId | None:
        """Resolve tenant ID from headers."""
        return headers.get(self._header_name)  # type: ignore

    def resolve_from_jwt(self, claims: dict[str, Any]) -> TId | None:
        """Resolve tenant ID from JWT claims."""
        return claims.get(self._jwt_claim)

    def resolve_from_query(self, params: dict[str, str]) -> TId | None:
        """Resolve tenant ID from query parameters."""
        return params.get(self._query_param)  # type: ignore


@runtime_checkable
class TenantResolver[TId](Protocol):
    """Protocol for tenant resolution.

    Type Parameters:
        TId: The type of tenant identifier.
    """

    async def resolve(self, tenant_id: TId) -> TenantInfo[TId] | None:
        """Resolve tenant by ID."""
        ...


@runtime_checkable
class TenantAwareRepository[T: BaseModel, TenantId](Protocol):
    """Generic repository with automatic tenant filtering.

    Type Parameters:
        T: Entity type.
        TenantId: Tenant identifier type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 18.2**
    """

    async def get_by_id(self, id: str, tenant_id: TenantId) -> T | None:
        """Get entity by ID within tenant scope."""
        ...

    async def get_all(
        self,
        tenant_id: TenantId,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> tuple[Sequence[T], int]:
        """Get all entities within tenant scope."""
        ...

    async def create(self, data: Any, tenant_id: TenantId) -> T:
        """Create entity within tenant scope."""
        ...

    async def update(self, id: str, data: Any, tenant_id: TenantId) -> T | None:
        """Update entity within tenant scope."""
        ...

    async def delete(self, id: str, tenant_id: TenantId) -> bool:
        """Delete entity within tenant scope."""
        ...


class TenantAwareRepositoryBase[T: BaseModel, TenantId](ABC):
    """Base implementation for tenant-aware repository.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 18.2**
    """

    def _get_current_tenant_id(self) -> TenantId:
        """Get current tenant ID from context."""
        tenant = TenantContext.get_current()
        if tenant is None:
            raise ValueError("No tenant in context")
        return tenant.id

    @abstractmethod
    async def get_by_id(self, id: str, tenant_id: TenantId | None = None) -> T | None:
        """Get entity by ID within tenant scope."""
        ...


@dataclass
class SchemaConfig:
    """Schema-per-tenant configuration.

    **Validates: Requirements 18.3**
    """

    default_schema: str = "public"
    schema_prefix: str = "tenant_"
    create_on_provision: bool = True


class TenantSchemaManager[TId]:
    """Manager for schema-per-tenant isolation.

    Type Parameters:
        TId: The type of tenant identifier.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 18.3**
    """

    def __init__(self, config: SchemaConfig) -> None:
        self._config = config

    def get_schema_name(self, tenant_id: TId) -> str:
        """Get schema name for tenant."""
        return f"{self._config.schema_prefix}{tenant_id}"

    def get_connection_schema(self, tenant: TenantInfo[TId]) -> str:
        """Get connection schema for tenant."""
        if tenant.schema_name:
            return tenant.schema_name
        return self.get_schema_name(tenant.id)


class TenantScopedCache[TId]:
    """Tenant-scoped cache key prefixing.

    Type Parameters:
        TId: The type of tenant identifier.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 18.4**
    """

    def __init__(self, prefix: str = "tenant") -> None:
        self._prefix = prefix

    def get_key(self, tenant_id: TId, key: str) -> str:
        """Get tenant-scoped cache key."""
        return f"{self._prefix}:{tenant_id}:{key}"

    def get_pattern(self, tenant_id: TId) -> str:
        """Get pattern for all tenant keys."""
        return f"{self._prefix}:{tenant_id}:*"


@dataclass(frozen=True, slots=True)
class TenantAuditEntry[TId]:
    """Audit entry with tenant context.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 18.5**
    """

    tenant_id: TId
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: str
    details: dict[str, Any] | None = None
