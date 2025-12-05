"""Users bounded context - Application Layer.

Provides CQRS handlers for User aggregate:
- Commands: Create, update, deactivate users
- Queries: Get, list, search users
- Projections: Event handlers for read model
- Read Model: Query-optimized DTOs

**Architecture: Vertical Slice - Users Bounded Context**
**Feature: architecture-restructuring-2025**
"""

from application.users.commands import CreateUserCommand, CreateUserHandler
from application.users.dtos import (
    ChangeEmailDTO,
    ChangePasswordDTO,
    CreateUserDTO,
    UpdateUserDTO,
    UserActivityReadDTO,
    UserDTO,
    UserListDTO,
    UserListReadDTO,
    UserReadDTO,
    UserSearchResultDTO,
)
from application.users.mappers import UserMapper
from application.users.queries import (
    GetUserByEmailHandler,
    GetUserByEmailQuery,
    GetUserByIdHandler,
    GetUserByIdQuery,
)
from application.users.read_model.projections import (
    UserProjectionHandler,
    UserReadModelProjector,
)

__all__ = [
    "ChangeEmailDTO",
    "ChangePasswordDTO",
    # Commands
    "CreateUserCommand",
    "CreateUserDTO",
    "CreateUserHandler",
    "GetUserByEmailHandler",
    "GetUserByEmailQuery",
    "GetUserByIdHandler",
    # Queries
    "GetUserByIdQuery",
    "UpdateUserDTO",
    # Write Model DTOs
    "UserDTO",
    "UserListDTO",
    # Read Model DTOs
    "UserReadDTO",
    "UserListReadDTO",
    "UserSearchResultDTO",
    "UserActivityReadDTO",
    # Mappers
    "UserMapper",
    # Projections
    "UserProjectionHandler",
    "UserReadModelProjector",
]
