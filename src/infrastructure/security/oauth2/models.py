"""OAuth2 data models.

**Feature: code-review-refactoring, Task 5.3: Extract models module**
**Validates: Requirements 4.4**
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel, Field

from .enums import OAuthProvider


@dataclass(frozen=True, slots=True)
class OAuthConfig:
    """OAuth2 provider configuration.

    Attributes:
        provider: OAuth provider type.
        client_id: OAuth client ID.
        client_secret: OAuth client secret.
        redirect_uri: Callback URL after authentication.
        scopes: Requested permission scopes.
        authorize_url: Authorization endpoint URL.
        token_url: Token exchange endpoint URL.
        userinfo_url: User info endpoint URL.
        jwks_url: JWKS endpoint for token verification (OIDC).
        request_timeout: HTTP request timeout in seconds.
    """

    provider: OAuthProvider
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...] = field(default_factory=tuple)
    authorize_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    jwks_url: str | None = None
    request_timeout: float = 30.0


class OAuthUserInfo(BaseModel):
    """Normalized user information from OAuth provider."""

    provider: OAuthProvider
    provider_user_id: str
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
    locale: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)


class OAuthTokenResponse(BaseModel):
    """OAuth token response from provider."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None


@dataclass(frozen=True, slots=True)
class OAuthState:
    """OAuth state for CSRF protection."""

    state: str
    nonce: str | None = None
    redirect_to: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_expired(self, max_age_seconds: int = 600) -> bool:
        """Check if state has expired.

        Args:
            max_age_seconds: Maximum age in seconds (default 10 minutes).

        Returns:
            True if state is expired.
        """
        age = (datetime.now(UTC) - self.created_at).total_seconds()
        return age > max_age_seconds
