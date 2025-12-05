"""Multi-tenancy support with automatic tenant filtering.

Organized into subpackages by responsibility:
- models/: Context management (TenantContext, get/set_current_tenant)
- repository/: TenantRepository with automatic filtering
- middleware/: ASGI middleware for tenant extraction

This module provides generic multi-tenant repository and middleware
for automatic tenant isolation in data access.

**Feature: enterprise-features-2025**
**Validates: Requirements 7.1, 7.2, 7.3**
"""

from application.services.multitenancy.middleware import (
    TenantMiddleware,
    require_tenant,
)
from application.services.multitenancy.models import (
    TenantContext,
    get_current_tenant,
    set_current_tenant,
)
from application.services.multitenancy.repository import (
    TenantAware,
    TenantRepository,
)

__all__ = [
    # Repository
    "TenantAware",
    # Context Management
    "TenantContext",
    # Middleware
    "TenantMiddleware",
    "TenantRepository",
    "get_current_tenant",
    "require_tenant",
    "set_current_tenant",
]
