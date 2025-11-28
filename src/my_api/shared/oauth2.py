"""OAuth2/OIDC provider for external authentication.

**Feature: api-architecture-analysis, Task 11.4: OAuth2/OIDC Integration**
**Validates: Requirements 5.1**

Supports Google, GitHub, Azure AD and generic OIDC providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field


class OAuthProvider(str, Enum):
    """Supported OAuth2 providers."""

    GOOGLE = "google"
    GITHUB = "github"
    AZURE_AD = "azure_ad"
    GENERIC = "generic"


@dataclass(frozen=True)
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



# Provider-specific default configurations
PROVIDER_CONFIGS: dict[OAuthProvider, dict[str, str]] = {
    OAuthProvider.GOOGLE: {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
    },
    OAuthProvider.GITHUB: {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "jwks_url": "",
    },
    OAuthProvider.AZURE_AD: {
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "jwks_url": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
    },
}


class OAuthUserInfo(BaseModel):
    """Normalized user information from OAuth provider.

    Attributes:
        provider: OAuth provider that authenticated the user.
        provider_user_id: User ID from the provider.
        email: User email address.
        email_verified: Whether email is verified.
        name: User display name.
        given_name: User first name.
        family_name: User last name.
        picture: URL to user profile picture.
        locale: User locale/language preference.
        raw_data: Original response from provider.
    """

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
    """OAuth token response from provider.

    Attributes:
        access_token: OAuth access token.
        token_type: Token type (usually "Bearer").
        expires_in: Token expiration in seconds.
        refresh_token: Optional refresh token.
        scope: Granted scopes.
        id_token: OIDC ID token (if available).
    """

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None


@dataclass(frozen=True)
class OAuthState:
    """OAuth state for CSRF protection.

    Attributes:
        state: Random state string.
        nonce: OIDC nonce for replay protection.
        redirect_to: URL to redirect after auth.
        created_at: State creation timestamp.
    """

    state: str
    nonce: str | None = None
    redirect_to: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self, max_age_seconds: int = 600) -> bool:
        """Check if state has expired.

        Args:
            max_age_seconds: Maximum age in seconds (default 10 minutes).

        Returns:
            True if state is expired.
        """
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > max_age_seconds


class OAuthError(Exception):
    """Base OAuth error."""

    def __init__(self, message: str, error_code: str = "OAUTH_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class OAuthConfigError(OAuthError):
    """OAuth configuration error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "OAUTH_CONFIG_ERROR")


class OAuthTokenError(OAuthError):
    """OAuth token exchange error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "OAUTH_TOKEN_ERROR")


class OAuthUserInfoError(OAuthError):
    """OAuth user info retrieval error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "OAUTH_USERINFO_ERROR")


class OAuthStateError(OAuthError):
    """OAuth state validation error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "OAUTH_STATE_ERROR")


@runtime_checkable
class StateStore(Protocol):
    """Protocol for OAuth state storage."""

    async def save_state(self, state: OAuthState) -> None:
        """Save OAuth state."""
        ...

    async def get_state(self, state_id: str) -> OAuthState | None:
        """Retrieve OAuth state by ID."""
        ...

    async def delete_state(self, state_id: str) -> None:
        """Delete OAuth state."""
        ...


class InMemoryStateStore:
    """In-memory OAuth state store for development/testing."""

    def __init__(self) -> None:
        self._states: dict[str, OAuthState] = {}

    async def save_state(self, state: OAuthState) -> None:
        """Save OAuth state."""
        self._states[state.state] = state

    async def get_state(self, state_id: str) -> OAuthState | None:
        """Retrieve OAuth state by ID."""
        return self._states.get(state_id)

    async def delete_state(self, state_id: str) -> None:
        """Delete OAuth state."""
        self._states.pop(state_id, None)

    def clear_expired(self, max_age_seconds: int = 600) -> int:
        """Remove expired states.

        Args:
            max_age_seconds: Maximum age in seconds.

        Returns:
            Number of states removed.
        """
        expired = [
            k for k, v in self._states.items() if v.is_expired(max_age_seconds)
        ]
        for key in expired:
            del self._states[key]
        return len(expired)


class BaseOAuthProvider(ABC):
    """Base class for OAuth2 providers."""

    def __init__(self, config: OAuthConfig) -> None:
        """Initialize OAuth provider.

        Args:
            config: OAuth configuration.
        """
        self._config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate OAuth configuration."""
        if not self._config.client_id:
            raise OAuthConfigError("client_id is required")
        if not self._config.client_secret:
            raise OAuthConfigError("client_secret is required")
        if not self._config.redirect_uri:
            raise OAuthConfigError("redirect_uri is required")

    @property
    def provider(self) -> OAuthProvider:
        """Get provider type."""
        return self._config.provider

    def get_authorization_url(
        self,
        state: str,
        nonce: str | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        """Generate authorization URL for OAuth flow.

        Args:
            state: CSRF protection state.
            nonce: OIDC nonce for replay protection.
            extra_params: Additional query parameters.

        Returns:
            Authorization URL to redirect user to.
        """
        params = {
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "response_type": "code",
            "state": state,
        }

        if self._config.scopes:
            params["scope"] = " ".join(self._config.scopes)

        if nonce:
            params["nonce"] = nonce

        if extra_params:
            params.update(extra_params)

        return f"{self._config.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokenResponse:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback.

        Returns:
            OAuth token response.

        Raises:
            OAuthTokenError: If token exchange fails.
        """
        data = {
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "code": code,
            "redirect_uri": self._config.redirect_uri,
            "grant_type": "authorization_code",
        }

        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._config.token_url,
                    data=data,
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return OAuthTokenResponse(**response.json())
            except httpx.HTTPStatusError as e:
                raise OAuthTokenError(
                    f"Token exchange failed: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise OAuthTokenError(f"Token request failed: {e}") from e

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user information from provider.

        Args:
            access_token: OAuth access token.

        Returns:
            Normalized user information.
        """
        ...

    async def refresh_token(self, refresh_token: str) -> OAuthTokenResponse:
        """Refresh OAuth tokens.

        Args:
            refresh_token: Refresh token.

        Returns:
            New token response.

        Raises:
            OAuthTokenError: If refresh fails.
        """
        data = {
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._config.token_url,
                    data=data,
                    timeout=30.0,
                )
                response.raise_for_status()
                return OAuthTokenResponse(**response.json())
            except httpx.HTTPStatusError as e:
                raise OAuthTokenError(f"Token refresh failed: {e.response.text}") from e
            except httpx.RequestError as e:
                raise OAuthTokenError(f"Refresh request failed: {e}") from e


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth2/OIDC provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize Google OAuth provider.

        Args:
            client_id: Google OAuth client ID.
            client_secret: Google OAuth client secret.
            redirect_uri: Callback URL.
            scopes: Permission scopes (defaults to openid, email, profile).
        """
        defaults = PROVIDER_CONFIGS[OAuthProvider.GOOGLE]
        config = OAuthConfig(
            provider=OAuthProvider.GOOGLE,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes or ("openid", "email", "profile"),
            authorize_url=defaults["authorize_url"],
            token_url=defaults["token_url"],
            userinfo_url=defaults["userinfo_url"],
            jwks_url=defaults["jwks_url"],
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from Google.

        Args:
            access_token: Google access token.

        Returns:
            Normalized user information.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self._config.userinfo_url,
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                return OAuthUserInfo(
                    provider=OAuthProvider.GOOGLE,
                    provider_user_id=data.get("sub", ""),
                    email=data.get("email"),
                    email_verified=data.get("email_verified", False),
                    name=data.get("name"),
                    given_name=data.get("given_name"),
                    family_name=data.get("family_name"),
                    picture=data.get("picture"),
                    locale=data.get("locale"),
                    raw_data=data,
                )
            except httpx.HTTPStatusError as e:
                raise OAuthUserInfoError(
                    f"Failed to get Google user info: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise OAuthUserInfoError(f"Google user info request failed: {e}") from e


class GitHubOAuthProvider(BaseOAuthProvider):
    """GitHub OAuth2 provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize GitHub OAuth provider.

        Args:
            client_id: GitHub OAuth client ID.
            client_secret: GitHub OAuth client secret.
            redirect_uri: Callback URL.
            scopes: Permission scopes (defaults to user:email).
        """
        defaults = PROVIDER_CONFIGS[OAuthProvider.GITHUB]
        config = OAuthConfig(
            provider=OAuthProvider.GITHUB,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes or ("user:email",),
            authorize_url=defaults["authorize_url"],
            token_url=defaults["token_url"],
            userinfo_url=defaults["userinfo_url"],
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from GitHub.

        Args:
            access_token: GitHub access token.

        Returns:
            Normalized user information.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient() as client:
            try:
                # Get basic user info
                response = await client.get(
                    self._config.userinfo_url,
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                # Get primary email (GitHub requires separate call)
                email = data.get("email")
                email_verified = False

                if not email:
                    email_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers=headers,
                        timeout=30.0,
                    )
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        for e in emails:
                            if e.get("primary"):
                                email = e.get("email")
                                email_verified = e.get("verified", False)
                                break

                # Parse name
                name = data.get("name") or data.get("login")
                name_parts = (name or "").split(" ", 1)
                given_name = name_parts[0] if name_parts else None
                family_name = name_parts[1] if len(name_parts) > 1 else None

                return OAuthUserInfo(
                    provider=OAuthProvider.GITHUB,
                    provider_user_id=str(data.get("id", "")),
                    email=email,
                    email_verified=email_verified,
                    name=name,
                    given_name=given_name,
                    family_name=family_name,
                    picture=data.get("avatar_url"),
                    locale=None,
                    raw_data=data,
                )
            except httpx.HTTPStatusError as e:
                raise OAuthUserInfoError(
                    f"Failed to get GitHub user info: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise OAuthUserInfoError(f"GitHub user info request failed: {e}") from e

