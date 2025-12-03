"""User management routes for admin operations.

**DEPRECATED**: This module uses mock storage and is replaced by
`interface.v1.users_router` which uses CQRS with real persistence.
This file is kept for reference only and will be removed in a future version.

**Feature: core-rbac-system**
**Part of: Core API (permanent)**
"""

import warnings

warnings.warn(
    "interface.v1.auth.users_router is deprecated. "
    "Use interface.v1.users_router instead.",
    DeprecationWarning,
    stacklevel=2,
)

from datetime import datetime, UTC
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from application.common.base.dto import ApiResponse, PaginatedResponse

router = APIRouter(prefix="/users", tags=["Users"])


# === DTOs ===


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    display_name: str | None
    is_active: bool
    is_verified: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    """User update request."""

    display_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class AssignRoleRequest(BaseModel):
    """Role assignment request."""

    role_name: str = Field(..., min_length=1, max_length=50)


class RoleResponse(BaseModel):
    """Role response."""

    id: str
    name: str
    description: str
    permissions: list[str]
    is_system: bool


# === Mock Storage (shared with auth router) ===

from interface.v1.auth.router import _users, _user_roles

# Predefined roles
_roles = {
    "admin": {
        "id": str(uuid4()),
        "name": "admin",
        "description": "Full system administrator",
        "permissions": [
            "read",
            "write",
            "delete",
            "admin",
            "manage_users",
            "manage_roles",
        ],
        "is_system": True,
    },
    "user": {
        "id": str(uuid4()),
        "name": "user",
        "description": "Standard user with read/write access",
        "permissions": ["read", "write"],
        "is_system": True,
    },
    "viewer": {
        "id": str(uuid4()),
        "name": "viewer",
        "description": "Read-only access",
        "permissions": ["read"],
        "is_system": True,
    },
    "moderator": {
        "id": str(uuid4()),
        "name": "moderator",
        "description": "Content moderator",
        "permissions": ["read", "write", "delete", "view_audit"],
        "is_system": True,
    },
}


# === Routes ===


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List all users",
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
) -> PaginatedResponse[UserResponse]:
    """List all users with pagination."""
    users = list(_users.values())

    if is_active is not None:
        users = [u for u in users if u["is_active"] == is_active]

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated = users[start:end]

    return PaginatedResponse(
        items=[
            UserResponse(
                id=u["id"],
                email=u["email"],
                display_name=u["display_name"],
                is_active=u["is_active"],
                is_verified=u.get("is_verified", False),
                roles=_user_roles.get(u["id"], []),
                created_at=u["created_at"],
                updated_at=u["updated_at"],
            )
            for u in paginated
        ],
        total=len(users),
        page=page,
        size=page_size,
    )


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Get user by ID",
)
async def get_user(user_id: str) -> ApiResponse[UserResponse]:
    """Get user details by ID."""
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return ApiResponse(
        data=UserResponse(
            id=user["id"],
            email=user["email"],
            display_name=user["display_name"],
            is_active=user["is_active"],
            is_verified=user.get("is_verified", False),
            roles=_user_roles.get(user_id, []),
            created_at=user["created_at"],
            updated_at=user["updated_at"],
        )
    )


@router.patch(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Update user",
)
async def update_user(
    user_id: str,
    data: UserUpdateRequest,
) -> ApiResponse[UserResponse]:
    """Update user details."""
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.display_name is not None:
        user["display_name"] = data.display_name
    if data.is_active is not None:
        user["is_active"] = data.is_active

    user["updated_at"] = datetime.now(UTC)

    return ApiResponse(
        data=UserResponse(
            id=user["id"],
            email=user["email"],
            display_name=user["display_name"],
            is_active=user["is_active"],
            is_verified=user.get("is_verified", False),
            roles=_user_roles.get(user_id, []),
            created_at=user["created_at"],
            updated_at=user["updated_at"],
        )
    )


@router.post(
    "/{user_id}/roles",
    response_model=ApiResponse[UserResponse],
    summary="Assign role to user",
)
async def assign_role(
    user_id: str,
    data: AssignRoleRequest,
) -> ApiResponse[UserResponse]:
    """Assign a role to a user."""
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.role_name not in _roles:
        raise HTTPException(
            status_code=400, detail=f"Role '{data.role_name}' not found"
        )

    if user_id not in _user_roles:
        _user_roles[user_id] = []

    if data.role_name not in _user_roles[user_id]:
        _user_roles[user_id].append(data.role_name)

    return ApiResponse(
        data=UserResponse(
            id=user["id"],
            email=user["email"],
            display_name=user["display_name"],
            is_active=user["is_active"],
            is_verified=user.get("is_verified", False),
            roles=_user_roles.get(user_id, []),
            created_at=user["created_at"],
            updated_at=user["updated_at"],
        )
    )


@router.delete(
    "/{user_id}/roles/{role_name}",
    response_model=ApiResponse[UserResponse],
    summary="Revoke role from user",
)
async def revoke_role(
    user_id: str,
    role_name: str,
) -> ApiResponse[UserResponse]:
    """Revoke a role from a user."""
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id in _user_roles and role_name in _user_roles[user_id]:
        _user_roles[user_id].remove(role_name)

    return ApiResponse(
        data=UserResponse(
            id=user["id"],
            email=user["email"],
            display_name=user["display_name"],
            is_active=user["is_active"],
            is_verified=user.get("is_verified", False),
            roles=_user_roles.get(user_id, []),
            created_at=user["created_at"],
            updated_at=user["updated_at"],
        )
    )


# === Roles Endpoints ===


@router.get(
    "/roles/list",
    response_model=ApiResponse[list[RoleResponse]],
    summary="List all roles",
)
async def list_roles() -> ApiResponse[list[RoleResponse]]:
    """List all available roles."""
    return ApiResponse(
        data=[
            RoleResponse(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                permissions=r["permissions"],
                is_system=r["is_system"],
            )
            for r in _roles.values()
        ]
    )
