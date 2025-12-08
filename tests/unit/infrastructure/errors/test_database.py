"""Tests for database errors module.

Tests for DatabaseError and ConnectionPoolError.
"""

import pytest

from infrastructure.errors.base import InfrastructureError
from infrastructure.errors.database import (
    ConnectionPoolError,
    DatabaseError,
)


class TestDatabaseError:
    """Tests for DatabaseError class."""

    def test_is_infrastructure_error(self) -> None:
        """DatabaseError should be an InfrastructureError."""
        error = DatabaseError("test")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = DatabaseError("connection failed")
        assert error.message == "connection failed"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = DatabaseError("query failed", {"query": "SELECT *"})
        assert error.details == {"query": "SELECT *"}

    def test_init_default_details(self) -> None:
        """Error should have empty dict details by default."""
        error = DatabaseError("test")
        assert error.details == {}

    def test_can_be_raised(self) -> None:
        """DatabaseError can be raised and caught."""
        with pytest.raises(DatabaseError):
            raise DatabaseError("test")

    def test_can_be_caught_as_infrastructure_error(self) -> None:
        """DatabaseError can be caught as InfrastructureError."""
        with pytest.raises(InfrastructureError):
            raise DatabaseError("test")

    def test_str_representation(self) -> None:
        """Error should have string representation."""
        error = DatabaseError("db error")
        assert "db error" in str(error)


class TestConnectionPoolError:
    """Tests for ConnectionPoolError class."""

    def test_is_database_error(self) -> None:
        """ConnectionPoolError should be a DatabaseError."""
        error = ConnectionPoolError("pool exhausted")
        assert isinstance(error, DatabaseError)

    def test_is_infrastructure_error(self) -> None:
        """ConnectionPoolError should be an InfrastructureError."""
        error = ConnectionPoolError("test")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = ConnectionPoolError("no connections available")
        assert error.message == "no connections available"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = ConnectionPoolError("timeout", {"pool_size": 10})
        assert error.details == {"pool_size": 10}

    def test_can_be_raised(self) -> None:
        """ConnectionPoolError can be raised and caught."""
        with pytest.raises(ConnectionPoolError):
            raise ConnectionPoolError("test")

    def test_can_be_caught_as_database_error(self) -> None:
        """ConnectionPoolError can be caught as DatabaseError."""
        with pytest.raises(DatabaseError):
            raise ConnectionPoolError("test")

    def test_pool_exhaustion_scenario(self) -> None:
        """Test typical pool exhaustion error."""
        error = ConnectionPoolError(
            "Connection pool exhausted",
            {"max_connections": 100, "active": 100, "waiting": 5},
        )
        assert error.message == "Connection pool exhausted"
        assert error.details["max_connections"] == 100

    def test_acquisition_timeout_scenario(self) -> None:
        """Test connection acquisition timeout error."""
        error = ConnectionPoolError(
            "Connection acquisition timeout",
            {"timeout_seconds": 30},
        )
        assert "timeout" in error.message.lower()
