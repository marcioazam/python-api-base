"""OAuth2/JWT security dependencies for FastAPI.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.6**
"""

from typing import Annotated
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials

from my_app.core.config.settings import get_settings


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False,
)

# HTTP Bearer scheme for API key authentication
http_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TokenPayload:
    """JWT token payload data."""
    
    sub: str  # Subject (user ID)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: str | None = None  # JWT ID
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class CurrentUser:
    """Current authenticated user context."""
    
    user_id: str
    email: str | None = None
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def has_any_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def has_all_permissions(self, *permissions: str) -> bool:
        """Check if user has all specified permissions."""
        return all(perm in self.permissions for perm in permissions)


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
) -> CurrentUser | None:
    """Get current user from JWT token (optional).
    
    Args:
        token: JWT token from Authorization header.
        
    Returns:
        CurrentUser if token is valid, None otherwise.
    """
    if not token:
        return None
    
    try:
        # TODO: Implement JWT validation with token_service
        # For now, return None to indicate no authentication
        return None
    except Exception:
        return None


async def get_current_user(
    user: CurrentUser | None = Depends(get_current_user_optional),
) -> CurrentUser:
    """Get current user from JWT token (required).
    
    Args:
        user: Optional current user from token.
        
    Returns:
        CurrentUser if authenticated.
        
    Raises:
        HTTPException: If not authenticated.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Get current active user.
    
    Args:
        user: Current authenticated user.
        
    Returns:
        CurrentUser if active.
        
    Raises:
        HTTPException: If user is not active.
    """
    # TODO: Check if user is active in database
    return user


# Type aliases for dependency injection
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
CurrentUserOptionalDep = Annotated[CurrentUser | None, Depends(get_current_user_optional)]
ActiveUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]


def require_roles(*roles: str):
    """Create a dependency that requires specific roles.
    
    Args:
        roles: Required role names.
        
    Returns:
        Dependency function.
    """
    async def role_checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_any_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(roles)}",
            )
        return user
    return role_checker


def require_permissions(*permissions: str):
    """Create a dependency that requires specific permissions.
    
    Args:
        permissions: Required permission names.
        
    Returns:
        Dependency function.
    """
    async def permission_checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_all_permissions(*permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permissions: {', '.join(permissions)}",
            )
        return user
    return permission_checker


# Common role dependencies
AdminUserDep = Annotated[CurrentUser, Depends(require_roles("admin"))]
ModeratorUserDep = Annotated[CurrentUser, Depends(require_roles("admin", "moderator"))]
