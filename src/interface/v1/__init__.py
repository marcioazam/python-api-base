"""API v1 routers.

Organized into subpackages by responsibility:
- core/: Core infrastructure routes (health, cache, infrastructure, JWKS)
- auth/: Authentication routes
- users/: User management routes
- items/: Item management routes
- features/: Advanced feature routes (Kafka, Storage, Sustainability)
- enterprise/: Enterprise features (RBAC, rate limiting, tasks)
- examples/: Example domain routes

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.1**
"""

from interface.v1.auth import auth_router
from interface.v1.core import cache_router, health_router, infrastructure_router, jwks_router
from interface.v1.enterprise import enterprise_router
from interface.v1.examples import examples_router
from interface.v1.features import kafka_router, storage_router, sustainability_router
from interface.v1.items import items_router
from interface.v1.users import users_router

__all__ = [
    "auth_router",
    "cache_router",
    "enterprise_router",
    "examples_router",
    "health_router",
    "infrastructure_router",
    "items_router",
    "jwks_router",
    "kafka_router",
    "storage_router",
    "sustainability_router",
    "users_router",
]
