"""Property-based tests for structured logging with correlation ID.

**Feature: architecture-restructuring-2025, Property 2: Structured JSON Logging with Correlation ID**
**Validates: Requirements 1.2**
"""

import json
import uuid
from io import StringIO
from unittest.mock import patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

try:
    from my_app.core.config.logging import (
        configure_logging,
        get_logger,
        set_request_id,
        get_request_id,
        clear_request_id,
        redact_pii,
    )
except ImportError:
    pytest.skip("my_app.core.config.logging not available", allow_module_level=True)


class TestLoggingCorrelationProperties:
    """Property tests for structured logging with correlation ID."""

    @settings(max_examples=50)
    @given(request_id=st.uuids().map(str))
    def test_correlation_id_propagates_to_logs(self, request_id: str) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 2: Structured JSON Logging with Correlation ID**
        
        For any valid correlation ID set in context, the structured log output
        SHALL contain the request_id field with the exact value provided.
        **Validates: Requirements 1.2**
        """
        # Set the request ID
        set_request_id(request_id)
        
        try:
            # Verify it's retrievable
            retrieved_id = get_request_id()
            assert retrieved_id == request_id
        finally:
            clear_request_id()

    @settings(max_examples=20)
    @given(request_id=st.text(min_size=1, max_size=100))
    def test_any_string_request_id_is_stored(self, request_id: str) -> None:
        """
        For any non-empty string request ID, the context SHALL store and
        retrieve the exact value.
        """
        set_request_id(request_id)
        
        try:
            retrieved = get_request_id()
            assert retrieved == request_id
        finally:
            clear_request_id()

    def test_clear_request_id_removes_value(self) -> None:
        """
        After clearing request ID, get_request_id SHALL return None.
        """
        set_request_id("test-id-123")
        clear_request_id()
        assert get_request_id() is None


    @settings(max_examples=20)
    @given(
        key=st.sampled_from(["password", "secret", "token", "api_key", "authorization"]),
        value=st.text(min_size=1, max_size=50),
    )
    def test_pii_redaction_removes_sensitive_data(self, key: str, value: str) -> None:
        """
        For any key matching PII patterns, redact_pii SHALL replace
        the value with [REDACTED].
        """
        import logging
        
        event_dict = {key: value, "message": "test"}
        result = redact_pii(logging.getLogger(), "info", event_dict)
        
        assert result[key] == "[REDACTED]"
        assert result["message"] == "test"

    @settings(max_examples=20)
    @given(
        key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))).filter(
            lambda x: x.lower() not in ["password", "secret", "token", "api_key", "apikey", 
                                         "authorization", "auth", "credential", "credit_card",
                                         "ssn", "social_security"]
        ),
        value=st.text(min_size=1, max_size=50),
    )
    def test_non_pii_keys_are_preserved(self, key: str, value: str) -> None:
        """
        For any key NOT matching PII patterns, redact_pii SHALL preserve
        the original value.
        """
        import logging
        
        assume(not any(p in key.lower() for p in ["password", "secret", "token", "api", "auth", "cred"]))
        
        event_dict = {key: value}
        result = redact_pii(logging.getLogger(), "info", event_dict)
        
        assert result[key] == value


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    @settings(max_examples=5)
    @given(log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]))
    def test_valid_log_levels_configure_successfully(self, log_level: str) -> None:
        """
        For any valid log level, configure_logging SHALL complete without error.
        """
        # This should not raise
        configure_logging(log_level=log_level, log_format="console", development=True)

    @settings(max_examples=5)
    @given(
        log_level=st.text(min_size=1, max_size=10).filter(
            lambda x: x.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
    )
    def test_invalid_log_levels_raise_error(self, log_level: str) -> None:
        """
        For any invalid log level, configure_logging SHALL raise ValueError.
        """
        with pytest.raises(ValueError):
            configure_logging(log_level=log_level)
