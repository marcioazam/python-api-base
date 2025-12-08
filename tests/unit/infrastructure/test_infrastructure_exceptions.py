"""Unit tests for infrastructure exception hierarchy.

**Feature: infrastructure-code-review**
**Validates: Requirements 8.2**
"""

import pytest

from infrastructure.errors import (
    AuditLogError,
    CacheError,
    ConfigurationError,
    ConnectionPoolError,
    DatabaseError,
    ExternalServiceError,
    InfrastructureError,
    TelemetryError,
    TokenStoreError,
    TokenValidationError,
)


class TestInfrastructureExceptionHierarchy:
    """Tests for exception inheritance structure."""

    def test_infrastructure_error_is_base_exception(self) -> None:
        """InfrastructureError should inherit from Exception."""
        assert issubclass(InfrastructureError, Exception)

    def test_database_error_inherits_from_infrastructure_error(self) -> None:
        """DatabaseError should inherit from InfrastructureError."""
        assert issubclass(DatabaseError, InfrastructureError)

    def test_connection_pool_error_inherits_from_database_error(self) -> None:
        """ConnectionPoolError should inherit from DatabaseError."""
        assert issubclass(ConnectionPoolError, DatabaseError)
        assert issubclass(ConnectionPoolError, InfrastructureError)

    def test_token_store_error_inherits_from_infrastructure_error(self) -> None:
        """TokenStoreError should inherit from InfrastructureError."""
        assert issubclass(TokenStoreError, InfrastructureError)

    def test_token_validation_error_inherits_from_token_store_error(self) -> None:
        """TokenValidationError should inherit from TokenStoreError."""
        assert issubclass(TokenValidationError, TokenStoreError)
        assert issubclass(TokenValidationError, InfrastructureError)

    def test_telemetry_error_inherits_from_infrastructure_error(self) -> None:
        """TelemetryError should inherit from InfrastructureError."""
        assert issubclass(TelemetryError, InfrastructureError)

    def test_audit_log_error_inherits_from_infrastructure_error(self) -> None:
        """AuditLogError should inherit from InfrastructureError."""
        assert issubclass(AuditLogError, InfrastructureError)

    def test_configuration_error_inherits_from_infrastructure_error(self) -> None:
        """ConfigurationError should inherit from InfrastructureError."""
        assert issubclass(ConfigurationError, InfrastructureError)

    def test_external_service_error_inherits_from_infrastructure_error(self) -> None:
        """ExternalServiceError should inherit from InfrastructureError."""
        assert issubclass(ExternalServiceError, InfrastructureError)

    def test_cache_error_inherits_from_infrastructure_error(self) -> None:
        """CacheError should inherit from InfrastructureError."""
        assert issubclass(CacheError, InfrastructureError)


class TestInfrastructureErrorMessages:
    """Tests for exception message handling."""

    def test_infrastructure_error_message(self) -> None:
        """InfrastructureError should store and return message."""
        error = InfrastructureError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"

    def test_infrastructure_error_with_details(self) -> None:
        """InfrastructureError should include details in string representation."""
        error = InfrastructureError("Test error", details={"key": "value", "count": 42})
        error_str = str(error)
        assert "Test error" in error_str
        assert "key=value" in error_str
        assert "count=42" in error_str

    def test_infrastructure_error_empty_details(self) -> None:
        """InfrastructureError with empty details should not show parentheses."""
        error = InfrastructureError("Test error", details={})
        assert str(error) == "Test error"

    def test_database_error_message(self) -> None:
        """DatabaseError should properly format message."""
        error = DatabaseError("Connection failed", details={"host": "localhost"})
        assert "Connection failed" in str(error)
        assert "host=localhost" in str(error)

    def test_external_service_error_attributes(self) -> None:
        """ExternalServiceError should store service_name and retry_after."""
        error = ExternalServiceError(
            "Service unavailable",
            service_name="payment-api",
            retry_after=30,
            details={"status_code": 503},
        )
        assert error.service_name == "payment-api"
        assert error.retry_after == 30
        assert error.details["status_code"] == 503


class TestExceptionCatching:
    """Tests for exception catching behavior."""

    def test_catch_infrastructure_error_catches_database_error(self) -> None:
        """Catching InfrastructureError should catch DatabaseError."""
        with pytest.raises(InfrastructureError):
            raise DatabaseError("DB error")

    def test_catch_infrastructure_error_catches_token_store_error(self) -> None:
        """Catching InfrastructureError should catch TokenStoreError."""
        with pytest.raises(InfrastructureError):
            raise TokenStoreError("Token error")

    def test_catch_database_error_catches_connection_pool_error(self) -> None:
        """Catching DatabaseError should catch ConnectionPoolError."""
        with pytest.raises(DatabaseError):
            raise ConnectionPoolError("Pool exhausted")

    def test_catch_token_store_error_catches_token_validation_error(self) -> None:
        """Catching TokenStoreError should catch TokenValidationError."""
        with pytest.raises(TokenStoreError):
            raise TokenValidationError("Invalid token")

    def test_specific_exception_not_caught_by_sibling(self) -> None:
        """DatabaseError should not catch TokenStoreError."""
        with pytest.raises(TokenStoreError):
            try:
                raise TokenStoreError("Token error")
            except DatabaseError:
                pytest.fail("DatabaseError should not catch TokenStoreError")
