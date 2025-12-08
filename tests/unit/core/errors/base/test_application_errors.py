"""Tests for application errors module.

Tests for ApplicationError and its subclasses.
"""

import pytest

from core.errors.base.application_errors import (
    ApplicationError,
    CommandHandlerError,
    ConcurrencyError,
    HandlerNotFoundError,
    InvalidCommandError,
    InvalidQueryError,
    QueryHandlerError,
    TransactionError,
    UseCaseError,
)


class TestApplicationError:
    """Tests for ApplicationError base class."""

    def test_default_values(self) -> None:
        """ApplicationError should have sensible defaults."""
        error = ApplicationError("test error")
        assert error.message == "test error"
        assert error.error_code == "APPLICATION_ERROR"
        assert error.status_code == 500

    def test_custom_values(self) -> None:
        """ApplicationError should accept custom values."""
        error = ApplicationError(
            message="custom error",
            error_code="CUSTOM_CODE",
            status_code=400,
            details={"key": "value"},
        )
        assert error.message == "custom error"
        assert error.error_code == "CUSTOM_CODE"
        assert error.status_code == 400
        assert error.details == {"key": "value"}

    def test_is_exception(self) -> None:
        """ApplicationError should be an Exception."""
        error = ApplicationError("test")
        assert isinstance(error, Exception)


class TestCommandHandlerError:
    """Tests for CommandHandlerError class."""

    def test_message_includes_command_type(self) -> None:
        """Error message should include command type."""
        error = CommandHandlerError("CreateUser", "validation failed")
        assert "CreateUser" in error.message
        assert "validation failed" in error.message

    def test_error_code(self) -> None:
        """Error should have correct error code."""
        error = CommandHandlerError("CreateUser", "error")
        assert error.error_code == "COMMAND_HANDLER_ERROR"

    def test_status_code(self) -> None:
        """Error should have 500 status code."""
        error = CommandHandlerError("CreateUser", "error")
        assert error.status_code == 500

    def test_details_include_command_type(self) -> None:
        """Details should include command type."""
        error = CommandHandlerError("CreateUser", "error")
        assert error.details["command_type"] == "CreateUser"

    def test_custom_details(self) -> None:
        """Error should merge custom details."""
        error = CommandHandlerError("CreateUser", "error", {"extra": "data"})
        assert error.details["command_type"] == "CreateUser"
        assert error.details["extra"] == "data"


class TestQueryHandlerError:
    """Tests for QueryHandlerError class."""

    def test_message_includes_query_type(self) -> None:
        """Error message should include query type."""
        error = QueryHandlerError("GetUser", "not found")
        assert "GetUser" in error.message
        assert "not found" in error.message

    def test_error_code(self) -> None:
        """Error should have correct error code."""
        error = QueryHandlerError("GetUser", "error")
        assert error.error_code == "QUERY_HANDLER_ERROR"

    def test_status_code(self) -> None:
        """Error should have 500 status code."""
        error = QueryHandlerError("GetUser", "error")
        assert error.status_code == 500

    def test_details_include_query_type(self) -> None:
        """Details should include query type."""
        error = QueryHandlerError("GetUser", "error")
        assert error.details["query_type"] == "GetUser"


class TestUseCaseError:
    """Tests for UseCaseError class."""

    def test_message_includes_use_case(self) -> None:
        """Error message should include use case name."""
        error = UseCaseError("CreateOrder", "insufficient stock")
        assert "CreateOrder" in error.message
        assert "insufficient stock" in error.message

    def test_error_code(self) -> None:
        """Error should have correct error code."""
        error = UseCaseError("CreateOrder", "error")
        assert error.error_code == "USE_CASE_ERROR"

    def test_details_include_use_case(self) -> None:
        """Details should include use case name."""
        error = UseCaseError("CreateOrder", "error")
        assert error.details["use_case"] == "CreateOrder"


class TestInvalidCommandError:
    """Tests for InvalidCommandError class."""

    def test_message_includes_command_and_reason(self) -> None:
        """Error message should include command type and reason."""
        error = InvalidCommandError("CreateUser", "email is required")
        assert "CreateUser" in error.message
        assert "email is required" in error.message

    def test_error_code(self) -> None:
        """Error should have correct error code."""
        error = InvalidCommandError("CreateUser", "reason")
        assert error.error_code == "INVALID_COMMAND"

    def test_status_code(self) -> None:
        """Error should have 400 status code."""
        error = InvalidCommandError("CreateUser", "reason")
        assert error.status_code == 400

    def test_details(self) -> None:
        """Details should include command type and reason."""
        error = InvalidCommandError("CreateUser", "email is required")
        assert error.details["command_type"] == "CreateUser"
        assert error.details["reason"] == "email is required"


class TestInvalidQueryError:
    """Tests for InvalidQueryError class."""

    def test_message_includes_query_and_reason(self) -> None:
        """Error message should include query type and reason."""
        error = InvalidQueryError("GetUser", "id is required")
        assert "GetUser" in error.message
        assert "id is required" in error.message

    def test_error_code(self) -> None:
        """Error should have correct error code."""
        error = InvalidQueryError("GetUser", "reason")
        assert error.error_code == "INVALID_QUERY"

    def test_status_code(self) -> None:
        """Error should have 400 status code."""
        error = InvalidQueryError("GetUser", "reason")
        assert error.status_code == 400


class TestHandlerNotFoundError:
    """Tests for HandlerNotFoundError class."""

    def test_message_includes_handler_and_message_type(self) -> None:
        """Error message should include handler and message type."""
        error = HandlerNotFoundError("command", "CreateUser")
        assert "command" in error.message
        assert "CreateUser" in error.message

    def test_error_code(self) -> None:
        """Error should have correct error code."""
        error = HandlerNotFoundError("command", "CreateUser")
        assert error.error_code == "HANDLER_NOT_FOUND"

    def test_status_code(self) -> None:
        """Error should have 500 status code."""
        error = HandlerNotFoundError("command", "CreateUser")
        assert error.status_code == 500

    def test_details(self) -> None:
        """Details should include handler and message type."""
        error = HandlerNotFoundError("query", "GetUser")
        assert error.details["handler_type"] == "query"
        assert error.details["message_type"] == "GetUser"


class TestConcurrencyError:
    """Tests for ConcurrencyError class."""

    def test_message_includes_entity_info(self) -> None:
        """Error message should include entity type and id."""
        error = ConcurrencyError("User", "user-123", 5, 7)
        assert "User" in error.message
        assert "user-123" in error.message

    def test_error_code(self) -> None:
        """Error should have correct error code."""
        error = ConcurrencyError("User", "user-123", 5, 7)
        assert error.error_code == "CONCURRENCY_ERROR"

    def test_status_code(self) -> None:
        """Error should have 409 status code."""
        error = ConcurrencyError("User", "user-123", 5, 7)
        assert error.status_code == 409

    def test_details(self) -> None:
        """Details should include all version info."""
        error = ConcurrencyError("User", "user-123", 5, 7)
        assert error.details["entity_type"] == "User"
        assert error.details["entity_id"] == "user-123"
        assert error.details["expected_version"] == 5
        assert error.details["actual_version"] == 7


class TestTransactionError:
    """Tests for TransactionError class."""

    def test_message_includes_operation(self) -> None:
        """Error message should include operation."""
        error = TransactionError("commit", "connection lost")
        assert "commit" in error.message
        assert "connection lost" in error.message

    def test_error_code(self) -> None:
        """Error should have correct error code."""
        error = TransactionError("commit", "error")
        assert error.error_code == "TRANSACTION_ERROR"

    def test_status_code(self) -> None:
        """Error should have 500 status code."""
        error = TransactionError("commit", "error")
        assert error.status_code == 500

    def test_details(self) -> None:
        """Details should include operation."""
        error = TransactionError("rollback", "error")
        assert error.details["operation"] == "rollback"
