"""Users API routes using CQRS pattern.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.1**
"""

from typing import Any, NoReturn

from fastapi import APIRouter, HTTPException, status

from application.common.dto import PaginatedResponse
from application.users.commands import (
    CreateUserCommand,
    DeleteUserCommand,
    UpdateUserCommand,
)
from application.users.commands.dtos import (
    CreateUserDTO,
    UpdateUserDTO,
    UserDTO,
    UserListDTO,
)
from application.users.queries import (
    CountUsersQuery,
    GetUserByIdQuery,
    ListUsersQuery,
)
from core.base.patterns.result import Err, Ok
from interface.dependencies import CommandBusDep, PaginationDep, QueryBusDep

router = APIRouter(prefix="/users", tags=["Users"])

# Error message constants
ERR_USER_NOT_FOUND = "User not found"
ERR_EMAIL_CONFLICT = "Email already registered"


def _aggregate_to_dto(user_aggregate: Any) -> UserDTO:
    """Convert user aggregate to UserDTO.

    Args:
        user_aggregate: User aggregate from command result.

    Returns:
        UserDTO with formatted data.
    """
    return UserDTO(
        id=user_aggregate.id,
        email=user_aggregate.email,
        username=user_aggregate.username,
        display_name=user_aggregate.display_name,
        is_active=user_aggregate.is_active,
        is_verified=user_aggregate.is_verified,
        created_at=user_aggregate.created_at.isoformat()
        if user_aggregate.created_at
        else None,
        updated_at=user_aggregate.updated_at.isoformat()
        if user_aggregate.updated_at
        else None,
    )


def _raise_error_response(error: Any, context: str = "operation") -> NoReturn:
    """Map domain errors to HTTP responses.

    Args:
        error: Error from Result pattern.
        context: Operation context for logging.

    Raises:
        HTTPException: Mapped HTTP error.
    """
    error_msg = str(error)
    error_lower = error_msg.lower()

    if "not found" in error_lower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_USER_NOT_FOUND,
        )
    if "already registered" in error_lower or "already exists" in error_lower:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_msg,
        )
    if "invalid" in error_lower or "password" in error_lower:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg,
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_msg,
    )


@router.get("", response_model=PaginatedResponse[UserListDTO])
async def list_users(
    query_bus: QueryBusDep,
    pagination: PaginationDep,
) -> PaginatedResponse[UserListDTO]:
    """List all users with pagination.

    Args:
        query_bus: Query bus dependency.
        pagination: Pagination parameters.

    Returns:
        Paginated list of users.
    """
    # Dispatch list query through query bus
    list_query = ListUsersQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        include_inactive=False,
    )
    list_result = await query_bus.dispatch(list_query)

    # Dispatch count query for accurate total
    count_query = CountUsersQuery(include_inactive=False)
    count_result = await query_bus.dispatch(count_query)

    # Handle results
    match (list_result, count_result):
        case (Ok(users), Ok(total_count)):
            user_dtos = [
                UserListDTO(
                    id=u.get("id", ""),
                    email=u.get("email", ""),
                    username=u.get("username"),
                    is_active=u.get("is_active", False),
                )
                for u in users
            ]
            return PaginatedResponse(
                items=user_dtos,
                total=total_count,
                page=pagination.page,
                size=pagination.page_size,
            )
        case (Err(error), _) | (_, Err(error)):
            _raise_error_response(error, "list_users")


@router.get("/{user_id}", response_model=UserDTO)
async def get_user(user_id: str, query_bus: QueryBusDep) -> UserDTO:
    """Get a user by ID.

    Args:
        user_id: User identifier.
        query_bus: Query bus dependency.

    Returns:
        User data.

    Raises:
        HTTPException: If user not found.
    """
    # Dispatch query through query bus
    query = GetUserByIdQuery(user_id=user_id)
    result = await query_bus.dispatch(query)

    # Handle result
    match result:
        case Ok(user_data):
            if user_data is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERR_USER_NOT_FOUND,
                )
            return UserDTO(
                id=user_data.get("id", ""),
                email=user_data.get("email", ""),
                username=user_data.get("username"),
                display_name=user_data.get("display_name"),
                is_active=user_data.get("is_active", False),
                is_verified=user_data.get("is_verified", False),
                created_at=user_data.get("created_at"),
                updated_at=user_data.get("updated_at"),
            )
        case Err(error):
            _raise_error_response(error, "get_user")


@router.post("", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
async def create_user(data: CreateUserDTO, command_bus: CommandBusDep) -> UserDTO:
    """Create a new user.

    Args:
        data: User creation data.
        command_bus: Command bus dependency.

    Returns:
        Created user data.

    Raises:
        HTTPException: If validation fails or email already exists.
    """
    # Create command from DTO
    command = CreateUserCommand(
        email=data.email,
        password=data.password,
        username=data.username,
        display_name=data.display_name,
    )

    # Dispatch command through command bus
    result = await command_bus.dispatch(command)

    # Handle result
    match result:
        case Ok(user_aggregate):
            return _aggregate_to_dto(user_aggregate)
        case Err(error):
            _raise_error_response(error, "create_user")


@router.patch("/{user_id}", response_model=UserDTO)
async def update_user(
    user_id: str, data: UpdateUserDTO, command_bus: CommandBusDep
) -> UserDTO:
    """Update a user.

    Args:
        user_id: User identifier.
        data: User update data.
        command_bus: Command bus dependency.

    Returns:
        Updated user data.

    Raises:
        HTTPException: If user not found or validation fails.
    """
    # Create command from DTO
    command = UpdateUserCommand(
        user_id=user_id,
        username=data.username,
        display_name=data.display_name,
    )

    # Dispatch command through command bus
    result = await command_bus.dispatch(command)

    # Handle result
    match result:
        case Ok(user_aggregate):
            return _aggregate_to_dto(user_aggregate)
        case Err(error):
            _raise_error_response(error, "update_user")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, command_bus: CommandBusDep) -> None:
    """Delete a user (soft delete/deactivate).

    Args:
        user_id: User identifier.
        command_bus: Command bus dependency.

    Raises:
        HTTPException: If user not found.
    """
    # Create delete command
    command = DeleteUserCommand(
        user_id=user_id,
        reason="User deletion requested via API",
    )

    # Dispatch command through command bus
    result = await command_bus.dispatch(command)

    # Handle result
    match result:
        case Ok(_):
            return
        case Err(error):
            _raise_error_response(error, "delete_user")
