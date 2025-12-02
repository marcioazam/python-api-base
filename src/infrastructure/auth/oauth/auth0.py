"""Auth0 OAuth provider with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R13.6 - Auth0Provider[TUser, TClaims]**
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel

from infrastructure.auth.oauth.provider import (
    OAuthProvider,
    OAuthConfig,
    AuthResult,
    TokenPair,
    Credentials,
    PasswordCredentials,
    OAuth2Credentials,
    InvalidTokenError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class Auth0Config(OAuthConfig):
    """Auth0-specific configuration.

    **Requirement: R13.6 - Auth0 integration**
    """

    domain: str = "your-tenant.auth0.com"
    audience: str = ""
    connection: str = "Username-Password-Authentication"

    @property
    def issuer(self) -> str:
        """Get issuer URL."""
        return f"https://{self.domain}/"

    @property
    def token_endpoint(self) -> str:
        """Get token endpoint URL."""
        return f"https://{self.domain}/oauth/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Get userinfo endpoint URL."""
        return f"https://{self.domain}/userinfo"

    @property
    def authorize_endpoint(self) -> str:
        """Get authorization endpoint URL."""
        return f"https://{self.domain}/authorize"

    @property
    def revoke_endpoint(self) -> str:
        """Get token revocation endpoint URL."""
        return f"https://{self.domain}/oauth/revoke"

    @property
    def jwks_uri(self) -> str:
        """Get JWKS URI."""
        return f"https://{self.domain}/.well-known/jwks.json"


# =============================================================================
# Auth0 Provider
# =============================================================================


class Auth0Provider[TUser: BaseModel, TClaims: BaseModel](
    OAuthProvider[TUser, TClaims]
):
    """Auth0 OAuth provider.

    **Requirement: R13.6 - Auth0Provider[TUser, TClaims] maps custom claims to TClaims**

    Type Parameters:
        TUser: User model type.
        TClaims: Claims model type.

    Example:
        ```python
        class User(BaseModel):
            id: str
            email: str
            name: str


        class Claims(BaseModel):
            sub: str
            email: str
            permissions: list[str]


        provider = Auth0Provider[User, Claims](
            config=Auth0Config(
                domain="your-tenant.auth0.com",
                client_id="client-id",
                client_secret="secret",
                audience="https://api.example.com",
            ),
            user_type=User,
            claims_type=Claims,
        )
        ```
    """

    def __init__(
        self,
        config: Auth0Config,
        user_type: type[TUser],
        claims_type: type[TClaims],
        namespace: str = "",
    ) -> None:
        """Initialize Auth0 provider.

        Args:
            config: Auth0 configuration.
            user_type: User model type.
            claims_type: Claims model type.
            namespace: Custom claims namespace (e.g., "https://myapp.com/").
        """
        super().__init__(config, user_type, claims_type)
        self._auth0_config = config
        self._namespace = namespace
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._config.timeout.total_seconds(),
            )
        return self._client

    async def authenticate(
        self,
        credentials: Credentials,
    ) -> AuthResult[TUser, TClaims]:
        """Authenticate with Auth0."""
        try:
            if isinstance(credentials, PasswordCredentials):
                return await self._password_flow(credentials)
            elif isinstance(credentials, OAuth2Credentials):
                return await self._auth_code_flow(credentials)
            else:
                return AuthResult.fail(
                    "unsupported_grant_type",
                    "Credentials type not supported",
                )
        except httpx.HTTPError as e:
            logger.error(f"Auth0 auth error: {e}")
            return AuthResult.fail("server_error", str(e))

    async def _password_flow(
        self,
        credentials: PasswordCredentials,
    ) -> AuthResult[TUser, TClaims]:
        """Resource owner password flow."""
        client = await self._get_client()

        response = await client.post(
            self._auth0_config.token_endpoint,
            json={
                "grant_type": "password",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "username": credentials.username,
                "password": credentials.password,
                "audience": self._auth0_config.audience,
                "scope": " ".join(self._config.scopes),
                "connection": self._auth0_config.connection,
            },
        )

        if response.status_code != 200:
            error_data = response.json()
            return AuthResult.fail(
                error_data.get("error", "auth_failed"),
                error_data.get("error_description"),
            )

        token_data = response.json()
        tokens = self._parse_tokens(token_data)

        user = await self._get_user_info(tokens.access_token)
        claims = await self.get_claims(tokens.access_token)

        return AuthResult.ok(user, claims, tokens)

    async def _auth_code_flow(
        self,
        credentials: OAuth2Credentials,
    ) -> AuthResult[TUser, TClaims]:
        """Authorization code flow."""
        client = await self._get_client()

        response = await client.post(
            self._auth0_config.token_endpoint,
            json={
                "grant_type": "authorization_code",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "code": credentials.code,
                "redirect_uri": credentials.redirect_uri,
            },
        )

        if response.status_code != 200:
            error_data = response.json()
            return AuthResult.fail(
                error_data.get("error", "auth_failed"),
                error_data.get("error_description"),
            )

        token_data = response.json()
        tokens = self._parse_tokens(token_data)

        user = await self._get_user_info(tokens.access_token)
        claims = await self.get_claims(tokens.access_token)

        return AuthResult.ok(user, claims, tokens)

    async def validate(self, token: str) -> TUser:
        """Validate token and return user."""
        # For Auth0, we validate by calling userinfo
        # In production, verify JWT with JWKS
        return await self._get_user_info(token)

    async def refresh(self, refresh_token: str) -> TokenPair[TClaims]:
        """Refresh access token."""
        client = await self._get_client()

        response = await client.post(
            self._auth0_config.token_endpoint,
            json={
                "grant_type": "refresh_token",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "refresh_token": refresh_token,
            },
        )

        if response.status_code != 200:
            raise InvalidTokenError("Invalid refresh token")

        token_data = response.json()
        return self._parse_tokens(token_data)

    async def get_claims(self, token: str) -> TClaims:
        """Extract claims from token."""
        import jwt

        try:
            decoded = jwt.decode(token, options={"verify_signature": False})

            # Map namespaced claims to flat structure
            if self._namespace:
                mapped = self._map_namespaced_claims(decoded)
                return self._parse_claims(mapped)

            return self._parse_claims(decoded)
        except jwt.PyJWTError as e:
            raise InvalidTokenError(f"Failed to decode token: {e}")

    async def revoke(self, token: str) -> bool:
        """Revoke refresh token."""
        client = await self._get_client()

        response = await client.post(
            self._auth0_config.revoke_endpoint,
            json={
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "token": token,
            },
        )

        return response.status_code == 200

    async def _get_user_info(self, token: str) -> TUser:
        """Get user info from userinfo endpoint."""
        client = await self._get_client()

        response = await client.get(
            self._auth0_config.userinfo_endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise InvalidTokenError("Failed to get user info")

        data = response.json()

        # Map Auth0 user info to user model
        # Auth0 uses 'sub' as user ID
        user_data = {
            "id": data.get("sub"),
            "email": data.get("email"),
            "name": data.get("name") or data.get("nickname"),
            **data,
        }

        return self._parse_user(user_data)

    def _parse_tokens(self, data: dict[str, Any]) -> TokenPair[TClaims]:
        """Parse token response."""
        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 86400),
            scope=data.get("scope"),
        )

    def _map_namespaced_claims(self, decoded: dict[str, Any]) -> dict[str, Any]:
        """Map namespaced claims to flat structure.

        **Requirement: R13.6 - Map custom claims to TClaims**

        Auth0 requires namespaced custom claims. This maps them
        back to a flat structure.
        """
        result = {}

        for key, value in decoded.items():
            if key.startswith(self._namespace):
                # Remove namespace prefix
                clean_key = key[len(self._namespace) :]
                result[clean_key] = value
            else:
                result[key] = value

        return result

    def get_permissions(self, claims: TClaims) -> list[str]:
        """Extract permissions from claims.

        Auth0 stores permissions in 'permissions' claim when using
        RBAC with API authorization.
        """
        claims_dict = claims.model_dump()
        return claims_dict.get("permissions", [])

    def get_authorization_url(
        self,
        state: str,
        connection: str | None = None,
    ) -> str:
        """Get authorization URL for login redirect.

        Args:
            state: CSRF state parameter.
            connection: Optional connection name.

        Returns:
            Authorization URL.
        """
        params = {
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._config.scopes),
            "audience": self._auth0_config.audience,
            "state": state,
        }

        if connection:
            params["connection"] = connection

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self._auth0_config.authorize_endpoint}?{query}"
