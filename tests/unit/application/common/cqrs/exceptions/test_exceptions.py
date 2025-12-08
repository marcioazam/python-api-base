"""Tests for CQRS exceptions module.

Tests for CQRSError, HandlerNotFoundError, HandlerAlreadyRegisteredError, MiddlewareError.
"""

import pytest

from application.common.cqrs.exceptions.exceptions import (
    CQRSError,
    HandlerAlreadyRegisteredError,
    HandlerNotFoundError,
    MiddlewareError,
)


class SampleCommand:
    """Sample command for testing."""

    pass


class AnotherCommand:
    """Another sample command for testing."""

    pass


class TestCQRSError:
    """Tests for CQRSError base exception."""

    def test_is_exception(self) -> None:
        """CQRSError should be an Exception."""
        assert issubclass(CQRSError, Exception)

    def test_can_be_raised(self) -> None:
        """CQRSError can be raised and caught."""
        with pytest.raises(CQRSError):
            raise CQRSError("test error")

    def test_message(self) -> None:
        """CQRSError should store message."""
        error = CQRSError("test message")
        assert str(error) == "test message"

    def test_empty_message(self) -> None:
        """CQRSError can have empty message."""
        error = CQRSError()
        assert str(error) == ""


class TestHandlerNotFoundError:
    """Tests for HandlerNotFoundError exception."""

    def test_is_cqrs_error(self) -> None:
        """HandlerNotFoundError should be a CQRSError."""
        assert issubclass(HandlerNotFoundError, CQRSError)

    def test_stores_command_type(self) -> None:
        """HandlerNotFoundError should store command type."""
        error = HandlerNotFoundError(SampleCommand)
        assert error.command_type is SampleCommand

    def test_message_includes_command_name(self) -> None:
        """Error message should include command type name."""
        error = HandlerNotFoundError(SampleCommand)
        assert "SampleCommand" in str(error)
        assert "No handler registered" in str(error)

    def test_different_command_types(self) -> None:
        """Error should work with different command types."""
        error1 = HandlerNotFoundError(SampleCommand)
        error2 = HandlerNotFoundError(AnotherCommand)
        assert error1.command_type is SampleCommand
        assert error2.command_type is AnotherCommand
        assert "SampleCommand" in str(error1)
        assert "AnotherCommand" in str(error2)

    def test_can_be_raised_and_caught(self) -> None:
        """HandlerNotFoundError can be raised and caught."""
        with pytest.raises(HandlerNotFoundError) as exc_info:
            raise HandlerNotFoundError(SampleCommand)
        assert exc_info.value.command_type is SampleCommand

    def test_can_be_caught_as_cqrs_error(self) -> None:
        """HandlerNotFoundError can be caught as CQRSError."""
        with pytest.raises(CQRSError):
            raise HandlerNotFoundError(SampleCommand)


class TestHandlerAlreadyRegisteredError:
    """Tests for HandlerAlreadyRegisteredError exception."""

    def test_is_cqrs_error(self) -> None:
        """HandlerAlreadyRegisteredError should be a CQRSError."""
        assert issubclass(HandlerAlreadyRegisteredError, CQRSError)

    def test_stores_command_type(self) -> None:
        """HandlerAlreadyRegisteredError should store command type."""
        error = HandlerAlreadyRegisteredError(SampleCommand)
        assert error.command_type is SampleCommand

    def test_message_includes_command_name(self) -> None:
        """Error message should include command type name."""
        error = HandlerAlreadyRegisteredError(SampleCommand)
        assert "SampleCommand" in str(error)
        assert "already registered" in str(error)

    def test_different_command_types(self) -> None:
        """Error should work with different command types."""
        error1 = HandlerAlreadyRegisteredError(SampleCommand)
        error2 = HandlerAlreadyRegisteredError(AnotherCommand)
        assert error1.command_type is SampleCommand
        assert error2.command_type is AnotherCommand

    def test_can_be_raised_and_caught(self) -> None:
        """HandlerAlreadyRegisteredError can be raised and caught."""
        with pytest.raises(HandlerAlreadyRegisteredError) as exc_info:
            raise HandlerAlreadyRegisteredError(SampleCommand)
        assert exc_info.value.command_type is SampleCommand

    def test_can_be_caught_as_cqrs_error(self) -> None:
        """HandlerAlreadyRegisteredError can be caught as CQRSError."""
        with pytest.raises(CQRSError):
            raise HandlerAlreadyRegisteredError(SampleCommand)


class TestMiddlewareError:
    """Tests for MiddlewareError exception."""

    def test_is_cqrs_error(self) -> None:
        """MiddlewareError should be a CQRSError."""
        assert issubclass(MiddlewareError, CQRSError)

    def test_stores_message(self) -> None:
        """MiddlewareError should store message."""
        error = MiddlewareError("middleware failed")
        assert error.message == "middleware failed"

    def test_str_representation(self) -> None:
        """Error string should be the message."""
        error = MiddlewareError("test error message")
        assert str(error) == "test error message"

    def test_can_be_raised_and_caught(self) -> None:
        """MiddlewareError can be raised and caught."""
        with pytest.raises(MiddlewareError) as exc_info:
            raise MiddlewareError("test")
        assert exc_info.value.message == "test"

    def test_can_be_caught_as_cqrs_error(self) -> None:
        """MiddlewareError can be caught as CQRSError."""
        with pytest.raises(CQRSError):
            raise MiddlewareError("test")

    def test_empty_message(self) -> None:
        """MiddlewareError can have empty message."""
        error = MiddlewareError("")
        assert error.message == ""
        assert str(error) == ""
