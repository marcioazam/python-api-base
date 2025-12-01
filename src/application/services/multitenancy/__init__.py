"""Multi-tenancy support with automatic tenant filtering.

This module provides generic multi-tenant repository and middleware
for automatic tenant isolation in data access.

Structure:
- models.py: Context management (TenantContext, get/set_current_tenant)
- repository.py: TenantRepository with automatic filtering
- middleware.py: ASGI middleware for tenant extraction

**Feature: enterprise-features-2025**
**Validates: Requirements 7.1, 7.2, 7.3**
"""

from .models import (
    TenantContext,
    get_current_tenant,
    set_current_tenant,
)
from .repository import (
    TenantAware,
    TenantRepository,
)
from .middleware import (
    TenantMiddleware,
    require_tenant,
)

__all__ = [
    # Context Management
    "TenantContext",
    "get_current_tenant",
    "set_current_tenant",
    # Repository
    "TenantAware",
    "TenantRepository",
    # Middleware
    "TenantMiddleware",
    "require_tenant",
]
