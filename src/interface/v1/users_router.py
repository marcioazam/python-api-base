"""Users API routes using CQRS pattern.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.1**
"""

from fastapi import APIRouter, HTTPException, status

from application.users.dto import (
    UserDTO,
    CreateUserDTO,
    UpdateUserDTO,
    UserListDTO,
)
from application.common.dto import PaginatedResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserListDTO])
async def list_users(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[UserListDTO]:
    """List all users with pagination.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        Paginated list of users.
    """
    # TODO: Implement with QueryBus dispatch
    return PaginatedResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserDTO)
async def get_user(user_id: str) -> UserDTO:
    """Get a user by ID.

    Args:
        user_id: User identifier.

    Returns:
        User data.

    Raises:
        HTTPException: If user not found.
    """
    # TODO: Implement with QueryBus dispatch
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User {user_id} not found",
    )


@router.post("", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
async def create_user(data: CreateUserDTO) -> UserDTO:
    """Create a new user.

    Args:
        data: User creation data.

    Returns:
        Created user data.

    Raises:
        HTTPException: If validation fails or email already exists.
    """
    # TODO: Implement with CommandBus dispatch
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented",
    )


@router.patch("/{user_id}", response_model=UserDTO)
async def update_user(user_id: str, data: UpdateUserDTO) -> UserDTO:
    """Update a user.

    Args:
        user_id: User identifier.
        data: User update data.

    Returns:
        Updated user data.

    Raises:
        HTTPException: If user not found or validation fails.
    """
    # TODO: Implement with CommandBus dispatch
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented",
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str) -> None:
    """Delete a user (soft delete/deactivate).

    Args:
        user_id: User identifier.

    Raises:
        HTTPException: If user not found.
    """
    # TODO: Implement with CommandBus dispatch
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented",
    )
