"""Users API routes.

Contains routes for user management.

**Feature: interface-restructuring-2025**
"""

from interface.v1.users.users_router import router as users_router

__all__ = [
    "users_router",
]
