"""Generic OAuth provider protocol with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R13.1, R13.2, R13.3 - Generic AuthProvider**
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Any

from pydantic import BaseModel


# =============================================================================
# Credentials
# =============================================================================


class Credentials(BaseModel):
    """Base credentials model."""

    pass


class PasswordCredentials(Credentials):
    """Username/password credentials."""

    username: str
    password: str


class TokenCredentials(Credentials):
    """Token-based credentials."""

    token: str
    token_type: str = "Bearer"


class OAuth2Credentials(Credentials):
    """OAuth2 authorization code credentials."""

    code: str
    redirect_uri: str
    state: str | None = None


# =============================================================================
# Token Pair
# =============================================================================


@dataclass(frozen=True, slots=True)
class TokenPair[TClaims]:
    """Access and refresh token pair.

    **Requirement: R13.7 - TokenPair[TClaims]**

    Type Parameters:
        TClaims: Claims type extracted from tokens.
    """

    access_token: str
    refresh_token: str | None
    token_type: str = "Bearer"
    expires_in: int = 3600
    scope: str | None = None
    claims: TClaims | None = None

    @property
    def expires_at(self) -> datetime:
        """Calculate expiration time."""
        return datetime.now(UTC) + timedelta(seconds=self.expires_in)


# =============================================================================
# Auth Result
# =============================================================================


@dataclass
class AuthResult[TUser, TClaims]:
    """Authentication result with typed user and claims.

    **Requirement: R13.2 - AuthResult[TUser, TClaims]**

    Type Parameters:
        TUser: User model type.
        TClaims: Claims model type.
    """

    success: bool
    user: TUser | None = None
    claims: TClaims | None = None
    tokens: TokenPair[TClaims] | None = None
    error: str | None = None
    error_description: str | None = None

    @classmethod
    def ok(
        cls,
        user: TUser,
        claims: TClaims,
        tokens: TokenPair[TClaims],
    ) -> "AuthResult[TUser, TClaims]":
        """Create successful result."""
        return cls(
            success=True,
            user=user,
            claims=claims,
            tokens=tokens,
        )

    @classmethod
    def fail(
        cls,
        error: str,
        description: str | None = None,
    ) -> "AuthResult[TUser, TClaims]":
        """Create failed result."""
        return cls(
            success=False,
            error=error,
            error_description=description,
        )


# =============================================================================
# Auth Error
# =============================================================================


class AuthError(Exception):
    """Authentication error.

    **Requirement: R13.3 - Typed AuthError**
    """

    def __init__(
        self,
        message: str,
        error_code: str = "auth_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class InvalidTokenError(AuthError):
    """Invalid or expired token."""

    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(message, error_code="invalid_token")


class InsufficientScopeError(AuthError):
    """Insufficient scope/permissions."""

    def __init__(self, required_scope: str) -> None:
        super().__init__(
            f"Insufficient scope: {required_scope} required",
            error_code="insufficient_scope",
            details={"required_scope": required_scope},
        )


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class OAuthConfig:
    """Base OAuth configuration."""

    client_id: str
    client_secret: str
    redirect_uri: str = ""
    scopes: list[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))


# =============================================================================
# OAuth Provider Protocol
# =============================================================================


class OAuthProvider[TUser: BaseModel, TClaims: BaseModel](ABC):
    """Generic OAuth provider protocol.

    **Requirement: R13.1 - Generic_AuthProvider[TUser, TClaims]**

    Type Parameters:
        TUser: User model type (Pydantic BaseModel).
        TClaims: Claims model type (Pydantic BaseModel).

    Example:
        ```python
        class User(BaseModel):
            id: str
            email: str
            name: str


        class Claims(BaseModel):
            sub: str
            email: str
            roles: list[str]


        provider = KeycloakProvider[User, Claims](
            config=KeycloakConfig(...),
            user_type=User,
            claims_type=Claims,
        )

        result = await provider.authenticate(credentials)
        if result.success:
            user = result.user  # Type: User
            claims = result.claims  # Type: Claims
        ```
    """

    def __init__(
        self,
        config: OAuthConfig,
        user_type: type[TUser],
        claims_type: type[TClaims],
    ) -> None:
        """Initialize provider.

        Args:
            config: OAuth configuration.
            user_type: User model type for deserialization.
            claims_type: Claims model type for deserialization.
        """
        self._config = config
        self._user_type = user_type
        self._claims_type = claims_type

    @abstractmethod
    async def authenticate(
        self,
        credentials: Credentials,
    ) -> AuthResult[TUser, TClaims]:
        """Authenticate with credentials.

        **Requirement: R13.2 - authenticate() returns AuthResult[TUser, TClaims]**

        Args:
            credentials: User credentials.

        Returns:
            Authentication result with user and claims.
        """
        ...

    @abstractmethod
    async def validate(
        self,
        token: str,
    ) -> TUser:
        """Validate token and return user.

        **Requirement: R13.3 - validate() returns TUser or raises AuthError**

        Args:
            token: Access token.

        Returns:
            Validated user.

        Raises:
            AuthError: If token is invalid.
        """
        ...

    @abstractmethod
    async def refresh(
        self,
        refresh_token: str,
    ) -> TokenPair[TClaims]:
        """Refresh access token.

        **Requirement: R13.7 - refresh() returns TokenPair[TClaims]**

        Args:
            refresh_token: Refresh token.

        Returns:
            New token pair.

        Raises:
            AuthError: If refresh token is invalid.
        """
        ...

    @abstractmethod
    async def get_claims(
        self,
        token: str,
    ) -> TClaims:
        """Extract claims from token.

        Args:
            token: Access token.

        Returns:
            Token claims.

        Raises:
            AuthError: If token is invalid.
        """
        ...

    @abstractmethod
    async def revoke(
        self,
        token: str,
    ) -> bool:
        """Revoke a token.

        Args:
            token: Token to revoke.

        Returns:
            True if revoked.
        """
        ...

    def _parse_user(self, data: dict[str, Any]) -> TUser:
        """Parse user from data."""
        return self._user_type.model_validate(data)

    def _parse_claims(self, data: dict[str, Any]) -> TClaims:
        """Parse claims from data."""
        return self._claims_type.model_validate(data)
