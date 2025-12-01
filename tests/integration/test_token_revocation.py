"""Integration tests for token revocation flow.

**Feature: api-architecture-review**
**Validates: Requirements 2.10**
"""

import pytest
from fastapi.testclient import TestClient

from my_app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_tokens(client: TestClient):
    """Get authentication tokens for test user."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "user", "password": "user123"},
    )
    assert response.status_code == 200
    return response.json()


class TestTokenRevocationFlow:
    """Integration tests for complete token revocation flow."""

    def test_login_returns_tokens(self, client: TestClient):
        """Login should return access and refresh tokens."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "user", "password": "user123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_access_token_works_before_revocation(
        self, client: TestClient, auth_tokens: dict
    ):
        """Access token should work before revocation."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user"

    def test_logout_revokes_refresh_token(
        self, client: TestClient, auth_tokens: dict
    ):
        """Logout should revoke the refresh token."""
        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )
        assert response.status_code == 200

        # Try to refresh with revoked token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )
        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower()

    def test_revoke_endpoint_revokes_token(
        self, client: TestClient, auth_tokens: dict
    ):
        """Revoke endpoint should invalidate the token."""
        # Revoke the refresh token
        response = client.post(
            "/api/v1/auth/revoke",
            json={"token": auth_tokens["refresh_token"]},
        )
        assert response.status_code == 200
        assert "revoked" in response.json()["message"].lower()

        # Try to refresh with revoked token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )
        assert response.status_code == 401

    def test_revoke_all_revokes_all_user_tokens(self, client: TestClient):
        """Revoke all should invalidate all tokens for the user."""
        # Login multiple times to create multiple tokens
        tokens = []
        for _ in range(3):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "user", "password": "user123"},
            )
            assert response.status_code == 200
            tokens.append(response.json())

        # Use first token to revoke all
        response = client.post(
            "/api/v1/auth/revoke-all",
            headers={"Authorization": f"Bearer {tokens[0]['access_token']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["revoked_count"] >= 3

        # Try to refresh with any of the revoked tokens
        for token_pair in tokens:
            response = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": token_pair["refresh_token"]},
            )
            assert response.status_code == 401

    def test_refresh_rotates_tokens(self, client: TestClient, auth_tokens: dict):
        """Refresh should return new tokens and revoke old refresh token."""
        # Refresh tokens
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )
        assert response.status_code == 200
        new_tokens = response.json()

        # New tokens should be different
        assert new_tokens["access_token"] != auth_tokens["access_token"]
        assert new_tokens["refresh_token"] != auth_tokens["refresh_token"]

        # Old refresh token should be revoked
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )
        assert response.status_code == 401

        # New refresh token should work
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_tokens["refresh_token"]},
        )
        assert response.status_code == 200

    def test_revoke_invalid_token_returns_400(self, client: TestClient):
        """Revoking an invalid token should return 400."""
        response = client.post(
            "/api/v1/auth/revoke",
            json={"token": "invalid-token-format"},
        )
        assert response.status_code == 400

    def test_revoke_nonexistent_token_returns_success(
        self, client: TestClient, auth_tokens: dict
    ):
        """Revoking a non-existent (but valid format) token should succeed."""
        # First revoke the token
        client.post(
            "/api/v1/auth/revoke",
            json={"token": auth_tokens["refresh_token"]},
        )

        # Try to revoke again
        response = client.post(
            "/api/v1/auth/revoke",
            json={"token": auth_tokens["refresh_token"]},
        )
        assert response.status_code == 200
        assert "not found" in response.json()["message"].lower() or "revoked" in response.json()["message"].lower()
