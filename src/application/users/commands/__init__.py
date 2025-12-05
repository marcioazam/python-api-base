"""User commands.

Organized into subpackages by responsibility:
- mutations/: Create, Update, Delete commands

**Feature: architecture-restructuring-2025**
"""

from application.users.commands.mutations import (
    CreateUserCommand,
    CreateUserHandler,
    DeleteUserCommand,
    DeleteUserHandler,
    UpdateUserCommand,
    UpdateUserHandler,
)

__all__ = [
    "CreateUserCommand",
    "CreateUserHandler",
    "DeleteUserCommand",
    "DeleteUserHandler",
    "UpdateUserCommand",
    "UpdateUserHandler",
]
