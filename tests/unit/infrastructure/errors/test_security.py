"""Tests for security errors module.

Tests for TokenStoreError, TokenValidationError, AuditLogError.
"""

import pytest

from infrastructure.errors.base import InfrastructureError
from infrastructure.errors.security import (
    AuditLogError,
    TokenStoreError,
    TokenValidationError,
)


class TestTokenStoreError:
    """Tests for TokenStoreError class."""

    def test_is_infrastructure_error(self) -> None:
        """TokenStoreError should be an InfrastructureError."""
        error = TokenStoreError("test")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = TokenStoreError("token storage failed")
        assert error.message == "token storage failed"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = TokenStoreError("store error", {"user_id": "123"})
        assert error.details == {"user_id": "123"}

    def test_can_be_raised(self) -> None:
        """TokenStoreError can be raised and caught."""
        with pytest.raises(TokenStoreError):
            raise TokenStoreError("test")

    def test_can_be_caught_as_infrastructure_error(self) -> None:
        """TokenStoreError can be caught as InfrastructureError."""
        with pytest.raises(InfrastructureError):
            raise TokenStoreError("test")


class TestTokenValidationError:
    """Tests for TokenValidationError class."""

    def test_is_token_store_error(self) -> None:
        """TokenValidationError should be a TokenStoreError."""
        error = TokenValidationError("invalid token")
        assert isinstance(error, TokenStoreError)

    def test_is_infrastructure_error(self) -> None:
        """TokenValidationError should be an InfrastructureError."""
        error = TokenValidationError("test")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = TokenValidationError("token expired")
        assert error.message == "token expired"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = TokenValidationError("invalid", {"reason": "expired"})
        assert error.details == {"reason": "expired"}

    def test_can_be_raised(self) -> None:
        """TokenValidationError can be raised and caught."""
        with pytest.raises(TokenValidationError):
            raise TokenValidationError("test")

    def test_can_be_caught_as_token_store_error(self) -> None:
        """TokenValidationError can be caught as TokenStoreError."""
        with pytest.raises(TokenStoreError):
            raise TokenValidationError("test")

    def test_expired_token_scenario(self) -> None:
        """Test expired token validation error."""
        error = TokenValidationError(
            "Token has expired",
            {"expired_at": "2024-01-01T00:00:00Z"},
        )
        assert "expired" in error.message.lower()

    def test_invalid_signature_scenario(self) -> None:
        """Test invalid signature validation error."""
        error = TokenValidationError(
            "Invalid token signature",
            {"algorithm": "RS256"},
        )
        assert "signature" in error.message.lower()


class TestAuditLogError:
    """Tests for AuditLogError class."""

    def test_is_infrastructure_error(self) -> None:
        """AuditLogError should be an InfrastructureError."""
        error = AuditLogError("audit failed")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = AuditLogError("failed to write audit log")
        assert error.message == "failed to write audit log"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = AuditLogError("write failed", {"action": "user.login"})
        assert error.details == {"action": "user.login"}

    def test_can_be_raised(self) -> None:
        """AuditLogError can be raised and caught."""
        with pytest.raises(AuditLogError):
            raise AuditLogError("test")

    def test_can_be_caught_as_infrastructure_error(self) -> None:
        """AuditLogError can be caught as InfrastructureError."""
        with pytest.raises(InfrastructureError):
            raise AuditLogError("test")

    def test_write_failure_scenario(self) -> None:
        """Test audit log write failure."""
        error = AuditLogError(
            "Failed to persist audit entry",
            {"event_type": "security.breach", "severity": "critical"},
        )
        assert error.details["severity"] == "critical"
