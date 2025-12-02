"""Keycloak OAuth provider with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R13.5 - KeycloakProvider[TUser, TClaims]**
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
class KeycloakConfig(OAuthConfig):
    """Keycloak-specific configuration.

    **Requirement: R13.5 - Keycloak integration**
    """

    server_url: str = "http://localhost:8080"
    realm: str = "master"
    verify_ssl: bool = True

    @property
    def token_endpoint(self) -> str:
        """Get token endpoint URL."""
        return f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Get userinfo endpoint URL."""
        return f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/userinfo"

    @property
    def introspect_endpoint(self) -> str:
        """Get token introspection endpoint URL."""
        return f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/token/introspect"

    @property
    def revoke_endpoint(self) -> str:
        """Get token revocation endpoint URL."""
        return f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/revoke"

    @property
    def jwks_uri(self) -> str:
        """Get JWKS URI."""
        return f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/certs"


# =============================================================================
# Keycloak Provider
# =============================================================================


class KeycloakProvider[TUser: BaseModel, TClaims: BaseModel](
    OAuthProvider[TUser, TClaims]
):
    """Keycloak OAuth provider.

    **Requirement: R13.5 - KeycloakProvider[TUser, TClaims] maps realm roles to TClaims**

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
            realm_access: dict[str, list[str]]


        provider = KeycloakProvider[User, Claims](
            config=KeycloakConfig(
                server_url="https://keycloak.example.com",
                realm="myrealm",
                client_id="myapp",
                client_secret="secret",
            ),
            user_type=User,
            claims_type=Claims,
        )
        ```
    """

    def __init__(
        self,
        config: KeycloakConfig,
        user_type: type[TUser],
        claims_type: type[TClaims],
        role_claim: str = "realm_access.roles",
    ) -> None:
        """Initialize Keycloak provider.

        Args:
            config: Keycloak configuration.
            user_type: User model type.
            claims_type: Claims model type.
            role_claim: Path to roles in token claims.
        """
        super().__init__(config, user_type, claims_type)
        self._keycloak_config = config
        self._role_claim = role_claim
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._config.timeout.total_seconds(),
                verify=self._keycloak_config.verify_ssl,
            )
        return self._client

    async def authenticate(
        self,
        credentials: Credentials,
    ) -> AuthResult[TUser, TClaims]:
        """Authenticate with Keycloak.

        Supports password and authorization code flows.
        """
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
            logger.error(f"Keycloak auth error: {e}")
            return AuthResult.fail("server_error", str(e))

    async def _password_flow(
        self,
        credentials: PasswordCredentials,
    ) -> AuthResult[TUser, TClaims]:
        """Resource owner password flow."""
        client = await self._get_client()

        response = await client.post(
            self._keycloak_config.token_endpoint,
            data={
                "grant_type": "password",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "username": credentials.username,
                "password": credentials.password,
                "scope": " ".join(self._config.scopes),
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

        # Get user info
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
            self._keycloak_config.token_endpoint,
            data={
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
        client = await self._get_client()

        # Introspect token
        response = await client.post(
            self._keycloak_config.introspect_endpoint,
            data={
                "token": token,
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
            },
        )

        if response.status_code != 200:
            raise InvalidTokenError()

        data = response.json()
        if not data.get("active", False):
            raise InvalidTokenError()

        return await self._get_user_info(token)

    async def refresh(self, refresh_token: str) -> TokenPair[TClaims]:
        """Refresh access token."""
        client = await self._get_client()

        response = await client.post(
            self._keycloak_config.token_endpoint,
            data={
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
            # Decode without verification for claims extraction
            # In production, verify with JWKS
            decoded = jwt.decode(token, options={"verify_signature": False})
            return self._parse_claims(decoded)
        except jwt.PyJWTError as e:
            raise InvalidTokenError(f"Failed to decode token: {e}")

    async def revoke(self, token: str) -> bool:
        """Revoke token."""
        client = await self._get_client()

        response = await client.post(
            self._keycloak_config.revoke_endpoint,
            data={
                "token": token,
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
            },
        )

        return response.status_code == 200

    async def _get_user_info(self, token: str) -> TUser:
        """Get user info from userinfo endpoint."""
        client = await self._get_client()

        response = await client.get(
            self._keycloak_config.userinfo_endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise InvalidTokenError("Failed to get user info")

        return self._parse_user(response.json())

    def _parse_tokens(self, data: dict[str, Any]) -> TokenPair[TClaims]:
        """Parse token response."""
        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 3600),
            scope=data.get("scope"),
        )

    def get_realm_roles(self, claims: TClaims) -> list[str]:
        """Extract realm roles from claims.

        **Requirement: R13.5 - Map realm roles to TClaims**
        """
        claims_dict = claims.model_dump()

        # Navigate to realm_access.roles
        parts = self._role_claim.split(".")
        value = claims_dict
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, [])
            else:
                return []

        return value if isinstance(value, list) else []
