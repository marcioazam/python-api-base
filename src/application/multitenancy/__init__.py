"""Multi-tenancy support with automatic tenant filtering.

This module provides generic multi-tenant repository and middleware
for automatic tenant isolation in data access.

**Feature: api-architecture-

Feature: file-size-compliance-phase2
"""

from .models import *
from .constants import *
from .service import *

__all__ = ['T', 'TenantAware', 'TenantContext', 'TenantMiddleware', 'TenantRepository', 'get_current_tenant', 'require_tenant', 'set_current_tenant']
