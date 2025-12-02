"""Unit tests for OAuth providers.

**Feature: enterprise-generics-2025**
**Requirement: R13 - Generic Authentication System**
"""

import pytest
from datetime import timedelta

from pydantic import BaseModel

from infrastructure.auth.oauth.provider import (
    OAuthConfig,
    TokenPair,
    AuthResult,
    AuthError,
    InvalidTokenError,
    Credentials,
    PasswordCredentials,
    OAuth2Credentials,
)
from infrastructure.auth.oauth.keycloak import KeycloakConfig, KeycloakProvider
from infrastructure.auth.oauth.auth0 import Auth0Config, Auth0Provider


# =============================================================================
# Test Models
# =============================================================================


class TestUser(BaseModel):
    """Test user model."""

    id: str
    email: str
    name: str


class TestClaims(BaseModel):
    """Test claims model."""

    sub: str
    email: str
    roles: list[str] = []
    permissions: list[str] = []


# =============================================================================
# Tests
# =============================================================================


class TestTokenPair:
    """Tests for TokenPair."""

    def test_token_pair_creation(self) -> None:
        """Test token pair can be created."""
        pair = TokenPair[TestClaims](
            access_token="access123",
            refresh_token="refresh456",
            expires_in=3600,
        )

        assert pair.access_token == "access123"
        assert pair.refresh_token == "refresh456"
        assert pair.token_type == "Bearer"

    def test_expires_at_calculation(self) -> None:
        """Test expiration time calculation."""
        pair = TokenPair[TestClaims](
            access_token="token",
            refresh_token=None,
            expires_in=3600,
        )

        # Should be approximately 1 hour from now
        from datetime import datetime, UTC

        now = datetime.now(UTC)
        diff = (pair.expires_at - now).total_seconds()

        assert 3590 < diff < 3610


class TestAuthResult:
    """Tests for AuthResult."""

    def test_success_result(self) -> None:
        """Test successful auth result."""
        user = TestUser(id="1", email="a@b.com", name="Test")
        claims = TestClaims(sub="1", email="a@b.com")
        tokens = TokenPair[TestClaims](
            access_token="token",
            refresh_token="refresh",
        )

        result = AuthResult.ok(user, claims, tokens)

        assert result.success
        assert result.user == user
        assert result.claims == claims
        assert result.tokens == tokens

    def test_failure_result(self) -> None:
        """Test failed auth result."""
        result = AuthResult[TestUser, TestClaims].fail(
            "invalid_grant",
            "Invalid username or password",
        )

        assert not result.success
        assert result.error == "invalid_grant"
        assert result.user is None


class TestCredentials:
    """Tests for credential types."""

    def test_password_credentials(self) -> None:
        """Test password credentials."""
        creds = PasswordCredentials(
            username="user@example.com",
            password="secret",
        )

        assert creds.username == "user@example.com"
        assert creds.password == "secret"

    def test_oauth2_credentials(self) -> None:
        """Test OAuth2 credentials."""
        creds = OAuth2Credentials(
            code="auth_code_123",
            redirect_uri="https://app.example.com/callback",
            state="csrf_state",
        )

        assert creds.code == "auth_code_123"
        assert creds.redirect_uri == "https://app.example.com/callback"


class TestAuthError:
    """Tests for AuthError."""

    def test_invalid_token_error(self) -> None:
        """Test InvalidTokenError."""
        error = InvalidTokenError()

        assert error.error_code == "invalid_token"
        assert "Invalid or expired token" in str(error)

    def test_auth_error_with_details(self) -> None:
        """Test AuthError with details."""
        error = AuthError(
            "Access denied",
            error_code="access_denied",
            details={"reason": "insufficient_permissions"},
        )

        assert error.error_code == "access_denied"
        assert error.details["reason"] == "insufficient_permissions"


class TestKeycloakConfig:
    """Tests for KeycloakConfig."""

    def test_default_config(self) -> None:
        """Test default Keycloak config."""
        config = KeycloakConfig(
            client_id="myapp",
            client_secret="secret",
        )

        assert config.server_url == "http://localhost:8080"
        assert config.realm == "master"

    def test_endpoint_urls(self) -> None:
        """Test endpoint URL generation."""
        config = KeycloakConfig(
            server_url="https://keycloak.example.com",
            realm="myrealm",
            client_id="app",
            client_secret="secret",
        )

        assert "myrealm" in config.token_endpoint
        assert "keycloak.example.com" in config.userinfo_endpoint
        assert "certs" in config.jwks_uri


class TestAuth0Config:
    """Tests for Auth0Config."""

    def test_default_config(self) -> None:
        """Test default Auth0 config."""
        config = Auth0Config(
            domain="tenant.auth0.com",
            client_id="client",
            client_secret="secret",
        )

        assert config.domain == "tenant.auth0.com"

    def test_endpoint_urls(self) -> None:
        """Test endpoint URL generation."""
        config = Auth0Config(
            domain="tenant.auth0.com",
            client_id="client",
            client_secret="secret",
        )

        assert "tenant.auth0.com" in config.token_endpoint
        assert config.issuer == "https://tenant.auth0.com/"
        assert "jwks.json" in config.jwks_uri


class TestKeycloakProvider:
    """Tests for KeycloakProvider."""

    @pytest.fixture
    def config(self) -> KeycloakConfig:
        """Create test config."""
        return KeycloakConfig(
            server_url="https://keycloak.example.com",
            realm="test",
            client_id="testapp",
            client_secret="secret",
        )

    @pytest.fixture
    def provider(self, config: KeycloakConfig) -> KeycloakProvider[TestUser, TestClaims]:
        """Create test provider."""
        return KeycloakProvider[TestUser, TestClaims](
            config=config,
            user_type=TestUser,
            claims_type=TestClaims,
        )

    def test_provider_initialization(
        self,
        provider: KeycloakProvider[TestUser, TestClaims],
    ) -> None:
        """Test provider can be initialized."""
        assert provider._user_type == TestUser
        assert provider._claims_type == TestClaims

    def test_get_realm_roles(
        self,
        provider: KeycloakProvider[TestUser, TestClaims],
    ) -> None:
        """Test extracting realm roles from claims."""
        # Create claims with realm_access.roles
        class ClaimsWithRoles(BaseModel):
            sub: str
            email: str
            realm_access: dict[str, list[str]] = {}

        provider_with_roles = KeycloakProvider[TestUser, ClaimsWithRoles](
            config=provider._keycloak_config,
            user_type=TestUser,
            claims_type=ClaimsWithRoles,
            role_claim="realm_access.roles",
        )

        claims = ClaimsWithRoles(
            sub="1",
            email="a@b.com",
            realm_access={"roles": ["admin", "user"]},
        )

        roles = provider_with_roles.get_realm_roles(claims)

        assert "admin" in roles
        assert "user" in roles


class TestAuth0Provider:
    """Tests for Auth0Provider."""

    @pytest.fixture
    def config(self) -> Auth0Config:
        """Create test config."""
        return Auth0Config(
            domain="tenant.auth0.com",
            client_id="testapp",
            client_secret="secret",
            audience="https://api.example.com",
        )

    @pytest.fixture
    def provider(self, config: Auth0Config) -> Auth0Provider[TestUser, TestClaims]:
        """Create test provider."""
        return Auth0Provider[TestUser, TestClaims](
            config=config,
            user_type=TestUser,
            claims_type=TestClaims,
        )

    def test_provider_initialization(
        self,
        provider: Auth0Provider[TestUser, TestClaims],
    ) -> None:
        """Test provider can be initialized."""
        assert provider._user_type == TestUser
        assert provider._claims_type == TestClaims

    def test_get_authorization_url(
        self,
        provider: Auth0Provider[TestUser, TestClaims],
    ) -> None:
        """Test authorization URL generation."""
        provider._config.redirect_uri = "https://app.example.com/callback"

        url = provider.get_authorization_url(state="csrf123")

        assert "tenant.auth0.com" in url
        assert "testapp" in url
        assert "csrf123" in url

    def test_map_namespaced_claims(
        self,
        provider: Auth0Provider[TestUser, TestClaims],
    ) -> None:
        """Test namespaced claim mapping."""
        provider._namespace = "https://myapp.com/"

        decoded = {
            "sub": "user123",
            "email": "user@example.com",
            "https://myapp.com/roles": ["admin", "user"],
            "https://myapp.com/org_id": "org123",
        }

        mapped = provider._map_namespaced_claims(decoded)

        assert mapped["sub"] == "user123"
        assert mapped["roles"] == ["admin", "user"]
        assert mapped["org_id"] == "org123"

    def test_get_permissions(
        self,
        provider: Auth0Provider[TestUser, TestClaims],
    ) -> None:
        """Test extracting permissions from claims."""
        claims = TestClaims(
            sub="1",
            email="a@b.com",
            permissions=["read:users", "write:users"],
        )

        perms = provider.get_permissions(claims)

        assert "read:users" in perms
        assert "write:users" in perms


class TestGenericTypeParameters:
    """Tests for generic type parameter behavior."""

    def test_provider_type_inference(self) -> None:
        """Test provider type parameters work correctly."""
        config = KeycloakConfig(
            client_id="app",
            client_secret="secret",
        )

        provider: KeycloakProvider[TestUser, TestClaims] = KeycloakProvider(
            config=config,
            user_type=TestUser,
            claims_type=TestClaims,
        )

        assert provider._user_type == TestUser
        assert provider._claims_type == TestClaims

    def test_auth_result_type_inference(self) -> None:
        """Test AuthResult type parameters."""
        user = TestUser(id="1", email="a@b.com", name="Test")
        claims = TestClaims(sub="1", email="a@b.com")
        tokens = TokenPair[TestClaims](access_token="t", refresh_token=None)

        result: AuthResult[TestUser, TestClaims] = AuthResult.ok(user, claims, tokens)

        assert isinstance(result.user, TestUser)
        assert isinstance(result.claims, TestClaims)

    def test_token_pair_generic_claims(self) -> None:
        """Test TokenPair with generic claims."""
        claims = TestClaims(sub="1", email="a@b.com", roles=["admin"])
        pair: TokenPair[TestClaims] = TokenPair(
            access_token="token",
            refresh_token="refresh",
            claims=claims,
        )

        assert pair.claims is not None
        assert pair.claims.roles == ["admin"]
