"""Multitenancy repository.

Contains repository for tenant data access.

**Feature: application-services-restructuring-2025**
"""

from application.services.multitenancy.repository.repository import (
    TenantAware,
    TenantRepository,
)

__all__ = [
    "TenantAware",
    "TenantRepository",
]
