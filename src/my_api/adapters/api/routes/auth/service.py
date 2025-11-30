"""auth service."""

from pydantic import BaseModel, Field
from my_api.core.auth.jwt import (
    JWTService,
)
from my_api.core.config import get_settings
from my_api.infrastructure.auth.token_store import InMemoryTokenStore, RefreshTokenStore


class TokenResponse(BaseModel):
    """Token pair response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")

class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., description="Refresh token to exchange")

class UserResponse(BaseModel):
    """Current user response."""

    id: str = Field(..., description="User ID")
    roles: list[str] = Field(default_factory=list, description="User roles")
    scopes: list[str] = Field(default_factory=list, description="Token scopes")

class MessageResponse(BaseModel):
    """Simple message response."""

    message: str

class RevokeTokenRequest(BaseModel):
    """Request to revoke a specific token."""

    token: str = Field(..., description="Token (access or refresh) to revoke")

class RevokeAllResponse(BaseModel):
    """Response for revoke all tokens operation."""

    message: str
    revoked_count: int = Field(..., description="Number of tokens revoked")

def get_jwt_service() -> JWTService:
    """Get JWT service instance."""
    global _jwt_service
    if _jwt_service is None:
        settings = get_settings()
        _jwt_service = JWTService(
            secret_key=settings.security.secret_key.get_secret_value(),
            algorithm=settings.security.algorithm,
            access_token_expire_minutes=settings.security.access_token_expire_minutes,
        )
    return _jwt_service

def get_token_store() -> RefreshTokenStore:
    """Get token store instance.

    Uses Redis if enabled in configuration, otherwise falls back to in-memory.
    """
    global _token_store
    if _token_store is None:
        # For sync context, use in-memory store
        # Redis store should be initialized at app startup
        _token_store = InMemoryTokenStore()
    return _token_store

def set_token_store(store: RefreshTokenStore) -> None:
    """Set the token store instance (for dependency injection).

    Args:
        store: Token store instance to use.
    """
    global _token_store
    _token_store = store
