"""Users API routes using CQRS pattern.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.1**
"""

from fastapi import APIRouter, HTTPException, status

from application.users.commands import (
    CreateUserCommand,
    UpdateUserCommand,
    DeleteUserCommand,
)
from application.users.queries import (
    GetUserByIdQuery,
    ListUsersQuery,
)
from application.users.commands.dtos import (
    UserDTO,
    CreateUserDTO,
    UpdateUserDTO,
    UserListDTO,
)
from application.common.base.dto import PaginatedResponse
from interface.dependencies import CommandBusDep, QueryBusDep, PaginationDep
from core.base.patterns.result import Ok, Err

router = APIRouter(prefix="/users", tags=["Users"])


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
    # Dispatch query through query bus
    query = ListUsersQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        include_inactive=False,
    )
    result = await query_bus.dispatch(query)

    # Handle result
    match result:
        case Ok(users):
            # Convert to UserListDTO format
            user_dtos = [
                UserListDTO(
                    id=u["id"],
                    email=u["email"],
                    username=u.get("username"),
                    is_active=u["is_active"],
                )
                for u in users
            ]
            return PaginatedResponse(
                items=user_dtos,
                total=len(user_dtos),  # TODO: Add count query for accurate total
                page=pagination.page,
                size=pagination.page_size,
            )
        case Err(error):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(error),
            )


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
                    detail=f"User {user_id} not found",
                )
            # Convert to UserDTO
            return UserDTO(
                id=user_data["id"],
                email=user_data["email"],
                username=user_data.get("username"),
                display_name=user_data.get("display_name"),
                is_active=user_data["is_active"],
                is_verified=user_data["is_verified"],
                created_at=user_data.get("created_at"),
                updated_at=user_data.get("updated_at"),
            )
        case Err(error):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(error),
            )


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
            # Convert aggregate to DTO
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
        case Err(error):
            # Handle specific errors
            error_msg = str(error)
            if "Email already registered" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=error_msg,
                )
            elif "Invalid email" in error_msg or "password" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=error_msg,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg,
                )


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
            # Convert aggregate to DTO
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
        case Err(error):
            error_msg = str(error)
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg,
                )


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
            # Success - return 204 No Content
            return None
        case Err(error):
            error_msg = str(error)
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg,
                )
