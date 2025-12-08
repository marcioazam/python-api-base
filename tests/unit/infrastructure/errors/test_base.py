"""Tests for infrastructure errors base module.

Tests for InfrastructureError class.
"""

import pytest

from infrastructure.errors.base import InfrastructureError


class TestInfrastructureError:
    """Tests for InfrastructureError class."""

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = InfrastructureError("test error")
        assert error.message == "test error"

    def test_init_default_details(self) -> None:
        """Error should have empty details by default."""
        error = InfrastructureError("test error")
        assert error.details == {}

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = InfrastructureError("test error", {"key": "value"})
        assert error.details == {"key": "value"}

    def test_init_none_details_becomes_empty_dict(self) -> None:
        """Error should convert None details to empty dict."""
        error = InfrastructureError("test error", None)
        assert error.details == {}

    def test_is_exception(self) -> None:
        """InfrastructureError should be an Exception."""
        error = InfrastructureError("test")
        assert isinstance(error, Exception)

    def test_str_without_details(self) -> None:
        """String representation should be message when no details."""
        error = InfrastructureError("test error")
        assert str(error) == "test error"

    def test_str_with_details(self) -> None:
        """String representation should include details."""
        error = InfrastructureError("test error", {"key": "value"})
        assert "test error" in str(error)
        assert "key=value" in str(error)

    def test_str_with_multiple_details(self) -> None:
        """String representation should include all details."""
        error = InfrastructureError("test error", {"a": 1, "b": 2})
        error_str = str(error)
        assert "test error" in error_str
        assert "a=1" in error_str
        assert "b=2" in error_str

    def test_can_be_raised(self) -> None:
        """InfrastructureError can be raised and caught."""
        with pytest.raises(InfrastructureError) as exc_info:
            raise InfrastructureError("test error", {"code": 500})
        assert exc_info.value.message == "test error"
        assert exc_info.value.details == {"code": 500}

    def test_format_message_empty_details(self) -> None:
        """_format_message should return just message for empty details."""
        error = InfrastructureError("test error")
        assert error._format_message() == "test error"

    def test_format_message_with_details(self) -> None:
        """_format_message should format details correctly."""
        error = InfrastructureError("test error", {"service": "db"})
        formatted = error._format_message()
        assert formatted == "test error (service=db)"

    def test_details_with_various_types(self) -> None:
        """Error should handle various detail value types."""
        error = InfrastructureError(
            "test error",
            {"string": "value", "int": 42, "bool": True, "none": None},
        )
        error_str = str(error)
        assert "string=value" in error_str
        assert "int=42" in error_str
        assert "bool=True" in error_str
        assert "none=None" in error_str
