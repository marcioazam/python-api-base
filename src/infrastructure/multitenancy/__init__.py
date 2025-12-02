"""Multitenancy module.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 18.1-18.5**
"""

from .tenant import (
    SchemaConfig,
    TenantAuditEntry,
    TenantAwareRepository,
    TenantAwareRepositoryBase,
    TenantContext,
    TenantInfo,
    TenantResolutionStrategy,
    TenantResolver,
    TenantSchemaManager,
    TenantScopedCache,
)

__all__ = [
    "SchemaConfig",
    "TenantAuditEntry",
    "TenantAwareRepository",
    "TenantAwareRepositoryBase",
    "TenantContext",
    "TenantInfo",
    "TenantResolutionStrategy",
    "TenantResolver",
    "TenantSchemaManager",
    "TenantScopedCache",
]
