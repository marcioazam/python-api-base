"""OAuth2 base provider.

**Feature: code-review-refactoring, Task 5.6: Extract base provider module**
**Validates: Requirements 4.1**
"""

from abc import ABC, abstractmethod
from urllib.parse import urlencode

import httpx

from .enums import OAuthProvider
from .exceptions import OAuthConfigError, OAuthTokenError
from .models import OAuthConfig, OAuthTokenResponse, OAuthUserInfo


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
                    timeout=self._config.request_timeout,
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
                    timeout=self._config.request_timeout,
                )
                response.raise_for_status()
                return OAuthTokenResponse(**response.json())
            except httpx.HTTPStatusError as e:
                raise OAuthTokenError(f"Token refresh failed: {e.response.text}") from e
            except httpx.RequestError as e:
                raise OAuthTokenError(f"Refresh request failed: {e}") from e
