"""RBAC endpoints.

**Feature: enterprise-generics-2025**
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from infrastructure.rbac import Permission

from .dependencies import get_audit_logger, get_rbac, get_role_registry
from .models import (
    ExampleAction,
    ExampleResource,
    ExampleUser,
    RBACCheckRequest,
    RBACCheckResponse,
)

router = APIRouter(tags=["RBAC"])


@router.post(
    "/rbac/check",
    response_model=RBACCheckResponse,
    summary="Check RBAC Permission",
)
async def check_rbac_permission(request: RBACCheckRequest) -> RBACCheckResponse:
    """Check RBAC permission."""
    rbac = get_rbac()

    user = ExampleUser(
        id=request.user_id,
        email=f"{request.user_id}@example.com",
        name="Test User",
        roles=request.user_roles,
    )

    try:
        resource = ExampleResource(request.resource)
        action = ExampleAction(request.action)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource '{request.resource}' or action '{request.action}'",
        )

    permission = Permission[ExampleResource, ExampleAction](
        resource=resource,
        action=action,
    )

    has_perm = rbac.has_permission(user, permission)

    audit = get_audit_logger()
    await audit.log_access(
        user_id=user.id,
        user_roles=user.roles,
        resource=resource,
        action=action,
        resource_id=None,
        granted=has_perm,
    )

    return RBACCheckResponse(
        has_permission=has_perm,
        checked_permission=str(permission),
        user_roles=request.user_roles,
    )


@router.get("/rbac/roles", summary="List Roles")
async def list_roles() -> list[dict[str, Any]]:
    """List all roles."""
    registry = get_role_registry()

    return [
        {
            "name": role.name,
            "description": role.description,
            "permissions": [str(p) for p in role.permissions],
            "parent": role.parent.name if role.parent else None,
        }
        for role in registry.list()
    ]
