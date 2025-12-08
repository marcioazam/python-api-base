"""Tests for external service errors module.

Tests for ExternalServiceError, CacheError, MessagingError, StorageError.
"""

import pytest

from infrastructure.errors.base import InfrastructureError
from infrastructure.errors.external import (
    CacheError,
    ExternalServiceError,
    MessagingError,
    StorageError,
)


class TestExternalServiceError:
    """Tests for ExternalServiceError class."""

    def test_is_infrastructure_error(self) -> None:
        """ExternalServiceError should be an InfrastructureError."""
        error = ExternalServiceError("test")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = ExternalServiceError("service failed")
        assert error.message == "service failed"

    def test_init_default_service_name(self) -> None:
        """Error should have None service_name by default."""
        error = ExternalServiceError("test")
        assert error.service_name is None

    def test_init_with_service_name(self) -> None:
        """Error should store service_name."""
        error = ExternalServiceError("test", service_name="payment-api")
        assert error.service_name == "payment-api"

    def test_init_default_retry_after(self) -> None:
        """Error should have None retry_after by default."""
        error = ExternalServiceError("test")
        assert error.retry_after is None

    def test_init_with_retry_after(self) -> None:
        """Error should store retry_after."""
        error = ExternalServiceError("test", retry_after=30)
        assert error.retry_after == 30

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = ExternalServiceError("test", details={"code": 500})
        assert error.details == {"code": 500}

    def test_init_all_params(self) -> None:
        """Error should accept all parameters."""
        error = ExternalServiceError(
            message="API timeout",
            service_name="user-service",
            retry_after=60,
            details={"endpoint": "/users"},
        )
        assert error.message == "API timeout"
        assert error.service_name == "user-service"
        assert error.retry_after == 60
        assert error.details == {"endpoint": "/users"}

    def test_can_be_raised(self) -> None:
        """ExternalServiceError can be raised and caught."""
        with pytest.raises(ExternalServiceError) as exc_info:
            raise ExternalServiceError("test", service_name="api")
        assert exc_info.value.service_name == "api"


class TestCacheError:
    """Tests for CacheError class."""

    def test_is_infrastructure_error(self) -> None:
        """CacheError should be an InfrastructureError."""
        error = CacheError("cache failed")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = CacheError("redis connection failed")
        assert error.message == "redis connection failed"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = CacheError("cache miss", {"key": "user:123"})
        assert error.details == {"key": "user:123"}

    def test_can_be_raised(self) -> None:
        """CacheError can be raised and caught."""
        with pytest.raises(CacheError):
            raise CacheError("test")


class TestMessagingError:
    """Tests for MessagingError class."""

    def test_is_infrastructure_error(self) -> None:
        """MessagingError should be an InfrastructureError."""
        error = MessagingError("queue failed")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = MessagingError("message publish failed")
        assert error.message == "message publish failed"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = MessagingError("queue full", {"queue": "orders"})
        assert error.details == {"queue": "orders"}

    def test_can_be_raised(self) -> None:
        """MessagingError can be raised and caught."""
        with pytest.raises(MessagingError):
            raise MessagingError("test")


class TestStorageError:
    """Tests for StorageError class."""

    def test_is_infrastructure_error(self) -> None:
        """StorageError should be an InfrastructureError."""
        error = StorageError("storage failed")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = StorageError("file upload failed")
        assert error.message == "file upload failed"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = StorageError("bucket not found", {"bucket": "uploads"})
        assert error.details == {"bucket": "uploads"}

    def test_can_be_raised(self) -> None:
        """StorageError can be raised and caught."""
        with pytest.raises(StorageError):
            raise StorageError("test")
