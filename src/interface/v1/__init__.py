"""API v1 routers.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.1**
"""

from interface.v1.health_router import router as health_router
from interface.v1.users_router import router as users_router

__all__ = [
    "health_router",
    "users_router",
]
