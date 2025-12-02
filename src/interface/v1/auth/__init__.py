"""Authentication and Authorization API routes.

**Feature: core-rbac-system**
**Part of: Core API (permanent)**
"""

from interface.v1.auth.router import router as auth_router
from interface.v1.auth.users_router import router as users_router

__all__ = ["auth_router", "users_router"]
