"""Unit tests for security errors.

**Feature: test-coverage-95-percent**
"""

import pytest

from core.errors.shared.security_errors import (
    SecurityModuleError,
    EncryptionError,
    DecryptionError,
    AuthenticationError,
    PatternValidationError,
)


class TestSecurityModuleError:
    """Tests for SecurityModuleError."""

    def test_is_exception(self) -> None:
        """Should be an exception."""
        error = SecurityModuleError("test error")
        assert isinstance(error, Exception)

    def test_message(self) -> None:
        """Should store message."""
        error = SecurityModuleError("test message")
        assert str(error) == "test message"


class TestEncryptionError:
    """Tests for EncryptionError."""

    def test_with_context(self) -> None:
        """Should store context."""
        context = {"key_id": "abc123", "algorithm": "AES-256"}
        error = EncryptionError("encryption failed", context=context)

        assert error.context == context
        assert str(error) == "encryption failed"

    def test_without_context(self) -> None:
        """Should have empty context by default."""
        error = EncryptionError("encryption failed")

        assert error.context == {}

    def test_inherits_from_security_module_error(self) -> None:
        """Should inherit from SecurityModuleError."""
        error = EncryptionError("test")
        assert isinstance(error, SecurityModuleError)


class TestDecryptionError:
    """Tests for DecryptionError."""

    def test_inherits_from_encryption_error(self) -> None:
        """Should inherit from EncryptionError."""
        error = DecryptionError("decryption failed")
        assert isinstance(error, EncryptionError)

    def test_with_context(self) -> None:
        """Should store context."""
        context = {"reason": "invalid key"}
        error = DecryptionError("decryption failed", context=context)

        assert error.context == context


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_inherits_from_decryption_error(self) -> None:
        """Should inherit from DecryptionError."""
        error = AuthenticationError("auth tag mismatch")
        assert isinstance(error, DecryptionError)

    def test_message(self) -> None:
        """Should store message."""
        error = AuthenticationError("authentication failed")
        assert str(error) == "authentication failed"


class TestPatternValidationError:
    """Tests for PatternValidationError."""

    def test_stores_pattern_and_reason(self) -> None:
        """Should store pattern and reason."""
        error = PatternValidationError(".*", "dangerous pattern")

        assert error.pattern == ".*"
        assert error.reason == "dangerous pattern"

    def test_message_format(self) -> None:
        """Should format message with pattern and reason."""
        error = PatternValidationError("(?!)", "invalid syntax")

        assert "(?!)" in str(error)
        assert "invalid syntax" in str(error)

    def test_inherits_from_security_module_error(self) -> None:
        """Should inherit from SecurityModuleError."""
        error = PatternValidationError("test", "reason")
        assert isinstance(error, SecurityModuleError)
