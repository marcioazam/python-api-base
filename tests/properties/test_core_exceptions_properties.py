"""Property-based tests for core exceptions module.

**Feature: core-code-review**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
"""

import json
import string
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from my_api.core.exceptions import (
    AppException,
    ErrorContext,
    ValidationError,
    EntityNotFoundError,
    AuthenticationError,
    AuthorizationError,
)


# Strategies for generating test data
error_code_strategy = st.text(
    min_size=1, max_size=50, alphabet=string.ascii_uppercase + "_"
)
message_strategy = st.text(min_size=1, max_size=200)
status_code_strategy = st.integers(min_value=400, max_value=599)


class TestExceptionSerializationConsistency:
    """Property tests for exception serialization.
    
    **Feature: core-code-review, Property 3: Exception Serialization Consistency**
    **Validates: Requirements 2.1, 2.2**
    """

    @given(
        message=message_strategy,
        error_code=error_code_strategy,
        status_code=status_code_strategy,
    )
    @settings(max_examples=100)
    def test_to_dict_contains_required_fields(
        self, message: str, error_code: str, status_code: int
    ):
        """For any AppException, to_dict() SHALL contain required fields."""
        assume(len(message) > 0 and len(error_code) > 0)
        
        exc = AppException(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )
        
        result = exc.to_dict()
        
        # Required fields must be present
        assert "message" in result
        assert "error_code" in result
        assert "status_code" in result
        assert "details" in result
        assert "correlation_id" in result
        assert "timestamp" in result
        
        # Values must match
        assert result["message"] == message
        assert result["error_code"] == error_code
        assert result["status_code"] == status_code

    @given(
        message=message_strategy,
        error_code=error_code_strategy,
    )
    @settings(max_examples=100)
    def test_to_dict_produces_valid_json(self, message: str, error_code: str):
        """For any AppException, to_dict() SHALL produce JSON-serializable output."""
        assume(len(message) > 0 and len(error_code) > 0)
        
        exc = AppException(message=message, error_code=error_code)
        result = exc.to_dict()
        
        # Should be JSON serializable
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        
        # Should round-trip correctly
        parsed = json.loads(json_str)
        assert parsed["message"] == message
        assert parsed["error_code"] == error_code

    @given(
        message=message_strategy,
        error_code=error_code_strategy,
    )
    @settings(max_examples=100)
    def test_correlation_id_is_unique(self, message: str, error_code: str):
        """For any two exceptions, correlation_ids SHALL be unique."""
        assume(len(message) > 0 and len(error_code) > 0)
        
        exc1 = AppException(message=message, error_code=error_code)
        exc2 = AppException(message=message, error_code=error_code)
        
        assert exc1.correlation_id != exc2.correlation_id

    @given(
        message=message_strategy,
        error_code=error_code_strategy,
    )
    @settings(max_examples=100)
    def test_timestamp_is_iso8601(self, message: str, error_code: str):
        """For any exception, timestamp SHALL be in ISO 8601 format."""
        assume(len(message) > 0 and len(error_code) > 0)
        
        exc = AppException(message=message, error_code=error_code)
        result = exc.to_dict()
        
        # Should be parseable as ISO 8601
        timestamp_str = result["timestamp"]
        parsed_time = datetime.fromisoformat(timestamp_str)
        assert isinstance(parsed_time, datetime)


class TestValidationErrorFormats:
    """Property tests for ValidationError format handling.
    
    **Feature: core-code-review**
    **Validates: Requirements 2.3**
    """

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=30, alphabet=string.ascii_lowercase),
            values=st.text(min_size=1, max_size=100),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_dict_format_normalized_to_list(self, errors_dict: dict):
        """For any dict errors, ValidationError SHALL normalize to list format."""
        assume(len(errors_dict) > 0)
        
        exc = ValidationError(errors=errors_dict)
        result = exc.to_dict()
        
        # Errors should be a list
        assert isinstance(result["details"]["errors"], list)
        
        # Each error should have field and message
        for error in result["details"]["errors"]:
            assert "field" in error
            assert "message" in error

    @given(
        st.lists(
            st.fixed_dictionaries({
                "field": st.text(min_size=1, max_size=30, alphabet=string.ascii_lowercase),
                "message": st.text(min_size=1, max_size=100),
            }),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_list_format_preserved(self, errors_list: list):
        """For any list errors, ValidationError SHALL preserve list format."""
        assume(len(errors_list) > 0)
        
        exc = ValidationError(errors=errors_list)
        result = exc.to_dict()
        
        # Errors should be a list with same length
        assert isinstance(result["details"]["errors"], list)
        assert len(result["details"]["errors"]) == len(errors_list)


class TestExceptionChaining:
    """Property tests for exception chaining.
    
    **Feature: core-code-review**
    **Validates: Requirements 2.4**
    """

    @given(
        outer_msg=message_strategy,
        inner_msg=message_strategy,
    )
    @settings(max_examples=100)
    def test_cause_chain_preserved(self, outer_msg: str, inner_msg: str):
        """For any chained exceptions, cause SHALL be preserved in to_dict()."""
        assume(len(outer_msg) > 0 and len(inner_msg) > 0)
        
        inner = AppException(message=inner_msg, error_code="INNER")
        
        try:
            raise inner
        except AppException as e:
            outer = AppException(message=outer_msg, error_code="OUTER")
            outer.__cause__ = e
        
        result = outer.to_dict()
        
        # Cause should be present
        assert "cause" in result
        assert result["cause"]["message"] == inner_msg
        assert result["cause"]["error_code"] == "INNER"


class TestErrorContext:
    """Property tests for ErrorContext."""

    def test_error_context_immutable(self):
        """ErrorContext SHALL be immutable (frozen dataclass)."""
        ctx = ErrorContext()
        
        with pytest.raises(Exception):  # FrozenInstanceError
            ctx.correlation_id = "new_id"

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_error_context_to_dict(self, request_path: str):
        """ErrorContext.to_dict() SHALL include all fields."""
        ctx = ErrorContext(request_path=request_path)
        result = ctx.to_dict()
        
        assert "correlation_id" in result
        assert "timestamp" in result
        assert "request_path" in result
        assert result["request_path"] == request_path
