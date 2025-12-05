"""Core API routes.

Contains core infrastructure routes (health, cache, infrastructure, JWKS).

**Feature: interface-restructuring-2025**
"""

from interface.v1.core.cache_router import router as cache_router
from interface.v1.core.health_router import router as health_router
from interface.v1.core.infrastructure_router import router as infrastructure_router
from interface.v1.core.jwks_router import router as jwks_router

__all__ = [
    "cache_router",
    "health_router",
    "infrastructure_router",
    "jwks_router",
]
