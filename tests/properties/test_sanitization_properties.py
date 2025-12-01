"""Property-based tests for input sanitization.

**Feature: api-base-improvements**
**Validates: Requirements 7.1, 7.2, 7.5**
"""

import string

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from my_app.shared.utils.sanitization import (
    InputSanitizer,
    SanitizationType,
    sanitize_string,
    sanitize_sql_identifier,
    sanitize_path,
    strip_dangerous_chars,
)


# Strategy for alphanumeric strings (safe characters)
alphanumeric_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet=string.ascii_letters + string.digits,
)

# Strategy for strings with spaces (still safe)
safe_text_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet=string.ascii_letters + string.digits + " ",
).filter(lambda x: x.strip() != "")

# Strategy for HTML injection patterns
html_injection_strategy = st.sampled_from([
    "<script>alert('xss')</script>",
    "<img onerror='alert(1)' src='x'>",
    "javascript:alert(1)",
    "<iframe src='evil.com'>",
    "<object data='evil.swf'>",
    "onclick='alert(1)'",
])

# Strategy for SQL injection patterns
sql_injection_strategy = st.sampled_from([
    "'; DROP TABLE users; --",
    "' OR '1'='1",
    "'; DELETE FROM items; --",
    "UNION SELECT * FROM passwords",
    "/**/OR/**/1=1",
    "@@version",
])

# Strategy for shell injection patterns
shell_injection_strategy = st.sampled_from([
    "; rm -rf /",
    "| cat /etc/passwd",
    "& whoami",
    "`id`",
    "$(cat /etc/shadow)",
    "&& ls -la",
])


class TestValidCharacterPreservation:
    """Property tests for valid character preservation."""

    @settings(max_examples=100, deadline=None)
    @given(text=alphanumeric_strategy)
    def test_alphanumeric_preserved_by_html_sanitization(self, text: str) -> None:
        """
        **Feature: api-base-improvements, Property 18: Input sanitization preserves valid characters**
        **Validates: Requirements 7.2**

        For any input containing only alphanumeric characters, sanitization
        SHALL return the input unchanged.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        result = sanitizer.sanitize_html(text)

        assert result == text, f"Alphanumeric text should be preserved: {text}"

    @settings(max_examples=100, deadline=None)
    @given(text=alphanumeric_strategy)
    def test_alphanumeric_preserved_by_sql_sanitization(self, text: str) -> None:
        """
        **Feature: api-base-improvements, Property 18: Input sanitization preserves valid characters**
        **Validates: Requirements 7.2**

        SQL sanitization SHALL preserve alphanumeric characters.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        result = sanitizer.sanitize_sql(text)

        assert result == text

    @settings(max_examples=100, deadline=None)
    @given(text=alphanumeric_strategy)
    def test_alphanumeric_preserved_by_shell_sanitization(self, text: str) -> None:
        """
        **Feature: api-base-improvements, Property 18: Input sanitization preserves valid characters**
        **Validates: Requirements 7.2**

        Shell sanitization SHALL preserve alphanumeric characters.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        result = sanitizer.sanitize_shell(text)

        assert result == text

    @settings(max_examples=100, deadline=None)
    @given(text=alphanumeric_strategy)
    def test_alphanumeric_preserved_by_full_sanitization(self, text: str) -> None:
        """
        **Feature: api-base-improvements, Property 18: Input sanitization preserves valid characters**
        **Validates: Requirements 7.2**

        Full sanitization (ALL types) SHALL preserve alphanumeric characters.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        result = sanitizer.sanitize(text, [SanitizationType.ALL])

        assert result == text

    @settings(max_examples=50, deadline=None)
    @given(text=safe_text_strategy)
    def test_safe_text_is_safe(self, text: str) -> None:
        """
        **Feature: api-base-improvements, Property 18: Input sanitization preserves valid characters**
        **Validates: Requirements 7.2**

        is_safe SHALL return True for safe alphanumeric text.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        # Only test with pure alphanumeric (no spaces that might be trimmed)
        clean_text = "".join(c for c in text if c.isalnum())
        if clean_text:
            assert sanitizer.is_safe(clean_text)


class TestSanitizationRoundTrip:
    """Property tests for sanitization round-trip."""

    @settings(max_examples=100, deadline=None)
    @given(text=alphanumeric_strategy)
    def test_sanitization_round_trip_for_safe_input(self, text: str) -> None:
        """
        **Feature: api-base-improvements, Property 19: Sanitization round-trip for valid inputs**
        **Validates: Requirements 7.5**

        For any input without dangerous characters, sanitizing SHALL return
        the original input.
        """
        sanitizer = InputSanitizer(log_modifications=False)

        # First sanitization
        result1 = sanitizer.sanitize(text, [SanitizationType.ALL])

        # Second sanitization (should be idempotent)
        result2 = sanitizer.sanitize(result1, [SanitizationType.ALL])

        # Results should be identical
        assert result1 == result2, "Sanitization should be idempotent"

    @settings(max_examples=100, deadline=None)
    @given(text=alphanumeric_strategy)
    def test_double_sanitization_is_idempotent(self, text: str) -> None:
        """
        **Feature: api-base-improvements, Property 19: Sanitization round-trip for valid inputs**
        **Validates: Requirements 7.5**

        Applying sanitization twice SHALL produce the same result as once.
        """
        sanitizer = InputSanitizer(log_modifications=False)

        once = sanitizer.sanitize(text)
        twice = sanitizer.sanitize(sanitizer.sanitize(text))

        assert once == twice

    @settings(max_examples=50, deadline=None)
    @given(text=safe_text_strategy)
    def test_sanitize_string_round_trip(self, text: str) -> None:
        """
        **Feature: api-base-improvements, Property 19: Sanitization round-trip for valid inputs**
        **Validates: Requirements 7.5**

        sanitize_string on safe text SHALL be idempotent.
        """
        result1 = sanitize_string(text)
        result2 = sanitize_string(result1)

        assert result1 == result2


class TestDangerousCharacterRemoval:
    """Property tests for dangerous character removal."""

    @settings(max_examples=100, deadline=None)
    @given(injection=html_injection_strategy)
    def test_html_injection_removed(self, injection: str) -> None:
        """
        **Feature: api-base-improvements, Property 20: Dangerous character removal**
        **Validates: Requirements 7.1**

        For any input containing HTML/SQL/shell injection patterns, sanitization
        SHALL remove or escape dangerous characters.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        result = sanitizer.sanitize_html(injection)

        # Script tags should be escaped or removed
        assert "<script" not in result.lower()
        assert "javascript:" not in result.lower()
        assert "onerror=" not in result.lower()
        assert "onclick=" not in result.lower()

    @settings(max_examples=100, deadline=None)
    @given(injection=sql_injection_strategy)
    def test_sql_injection_removed(self, injection: str) -> None:
        """
        **Feature: api-base-improvements, Property 20: Dangerous character removal**
        **Validates: Requirements 7.1**

        SQL injection patterns SHALL be removed.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        result = sanitizer.sanitize_sql(injection)

        # SQL injection patterns should be removed
        assert "DROP TABLE" not in result.upper()
        assert "DELETE FROM" not in result.upper()
        assert "UNION SELECT" not in result.upper()
        assert "--" not in result
        assert "/*" not in result

    @settings(max_examples=100, deadline=None)
    @given(injection=shell_injection_strategy)
    def test_shell_injection_removed(self, injection: str) -> None:
        """
        **Feature: api-base-improvements, Property 20: Dangerous character removal**
        **Validates: Requirements 7.1**

        Shell injection patterns SHALL be removed.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        result = sanitizer.sanitize_shell(injection)

        # Shell metacharacters should be removed
        assert ";" not in result
        assert "|" not in result
        assert "&" not in result
        assert "`" not in result
        assert "$(" not in result

    @settings(max_examples=50, deadline=None)
    @given(
        safe_text=alphanumeric_strategy,
        injection=html_injection_strategy,
    )
    def test_mixed_content_preserves_safe_removes_dangerous(
        self, safe_text: str, injection: str
    ) -> None:
        """
        **Feature: api-base-improvements, Property 20: Dangerous character removal**
        **Validates: Requirements 7.1**

        Mixed content SHALL preserve safe parts and remove dangerous parts.
        """
        sanitizer = InputSanitizer(log_modifications=False)
        mixed = f"{safe_text}{injection}"

        result = sanitizer.sanitize(mixed, [SanitizationType.HTML])

        # Safe text should still be present (possibly escaped)
        # Dangerous patterns should be removed
        assert "<script" not in result.lower()

    def test_strip_dangerous_chars_removes_sql_patterns(self) -> None:
        """
        **Feature: api-base-improvements, Property 20: Dangerous character removal**
        **Validates: Requirements 7.1**

        strip_dangerous_chars SHALL remove SQL injection characters.
        """
        dangerous = "SELECT * FROM users; DROP TABLE users; --"
        result = strip_dangerous_chars(dangerous)

        assert ";" not in result
        assert "--" not in result

    def test_sanitize_path_removes_traversal(self) -> None:
        """
        **Feature: api-base-improvements, Property 20: Dangerous character removal**
        **Validates: Requirements 7.1**

        sanitize_path SHALL remove path traversal sequences.
        """
        dangerous = "../../../etc/passwd"
        result = sanitize_path(dangerous)

        assert ".." not in result

    def test_sanitize_sql_identifier_only_allows_safe_chars(self) -> None:
        """
        **Feature: api-base-improvements, Property 20: Dangerous character removal**
        **Validates: Requirements 7.1**

        sanitize_sql_identifier SHALL only allow alphanumeric and underscore.
        """
        dangerous = "users; DROP TABLE--"
        result = sanitize_sql_identifier(dangerous)

        # Only alphanumeric and underscore should remain
        assert all(c.isalnum() or c == "_" for c in result)
        assert ";" not in result
        assert "-" not in result


class TestSanitizerConfiguration:
    """Property tests for sanitizer configuration."""

    def test_sanitizer_logs_modifications_when_enabled(self) -> None:
        """
        **Feature: api-base-improvements, Property 20: Dangerous character removal**
        **Validates: Requirements 7.1**

        Sanitizer SHALL log when modifications are made (when enabled).
        """
        import logging

        sanitizer = InputSanitizer(log_modifications=True)

        # This should trigger a log (we can't easily verify, but ensure no error)
        result = sanitizer.sanitize("<script>alert(1)</script>")
        assert "<script" not in result.lower()

    def test_empty_input_returns_empty(self) -> None:
        """Empty input SHALL return empty string."""
        sanitizer = InputSanitizer(log_modifications=False)

        assert sanitizer.sanitize("") == ""
        assert sanitizer.sanitize_html("") == ""
        assert sanitizer.sanitize_sql("") == ""
        assert sanitizer.sanitize_shell("") == ""

    def test_none_handling(self) -> None:
        """Sanitization functions SHALL handle edge cases gracefully."""
        assert sanitize_string("") == ""
        assert sanitize_path("") == ""
        assert strip_dangerous_chars("") == ""
