"""User queries.

Organized into subpackages by responsibility:
- read/: Read queries (Get, List, Count)

**Feature: architecture-restructuring-2025**
"""

from application.users.queries.read import (
    CountUsersHandler,
    CountUsersQuery,
    GetUserByEmailHandler,
    GetUserByEmailQuery,
    GetUserByIdHandler,
    GetUserByIdQuery,
    ListUsersHandler,
    ListUsersQuery,
)

__all__ = [
    "CountUsersHandler",
    "CountUsersQuery",
    "GetUserByEmailHandler",
    "GetUserByEmailQuery",
    "GetUserByIdHandler",
    "GetUserByIdQuery",
    "ListUsersHandler",
    "ListUsersQuery",
]
