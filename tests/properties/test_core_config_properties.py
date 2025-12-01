"""Property-based tests for core configuration module.

**Feature: core-code-review**
**Validates: Requirements 1.1, 1.3, 1.4**
"""

import os
import string
from unittest.mock import patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from pydantic import ValidationError

from my_app.core.config import (
    DatabaseSettings,
    SecuritySettings,
    redact_url_credentials,
)


class TestSecretKeyEntropyValidation:
    """Property tests for secret key entropy validation.

    **Feature: core-code-review, Property 1: Secret Key Entropy Validation**
    **Validates: Requirements 1.1**
    """

    @given(st.text(min_size=32, max_size=128, alphabet=string.ascii_letters + string.digits))
    @settings(max_examples=100)
    def test_valid_secret_keys_accepted(self, secret: str):
        """For any secret key >= 32 chars, validation SHALL pass."""
        assume(len(secret) >= 32)

        with patch.dict(os.environ, {"SECURITY__SECRET_KEY": secret}):
            settings_obj = SecuritySettings()
            assert len(settings_obj.secret_key.get_secret_value()) >= 32

    @given(st.text(min_size=1, max_size=31, alphabet=string.ascii_letters + string.digits))
    @settings(max_examples=100)
    def test_short_secret_keys_rejected(self, secret: str):
        """For any secret key < 32 chars, validation SHALL raise ValueError."""
        assume(0 < len(secret) < 32)

        with patch.dict(os.environ, {"SECURITY__SECRET_KEY": secret}):
            with pytest.raises(ValidationError) as exc_info:
                SecuritySettings()

            error_str = str(exc_info.value)
            assert "32" in error_str or "min_length" in error_str.lower()


class TestDatabaseUrlCredentialRedaction:
    """Property tests for database URL credential redaction.

    **Feature: core-code-review, Property 2: Database URL Credential Redaction**
    **Validates: Requirements 1.3**
    """

    def test_password_redacted_examples(self):
        """For any URL with credentials, password SHALL NOT appear in redacted output."""
        test_cases = [
            ("user", "secretpass123", "localhost", "mydb"),
            ("admin", "P@ssw0rd!2025", "db.example.com", "production"),
            ("dbuser", "verylongpassword12345", "192.168.1.1", "testdb"),
        ]

        for username, password, host, db_name in test_cases:
            url = f"postgresql://{username}:{password}@{host}/{db_name}"
            redacted = redact_url_credentials(url)

            assert password not in redacted, f"Password visible in: {redacted}"
            assert "[REDACTED]" in redacted, f"REDACTED marker missing in: {redacted}"
            assert username in redacted, f"Username missing in: {redacted}"

    def test_url_without_credentials_unchanged(self):
        """For any URL without credentials, output SHALL be unchanged."""
        urls = [
            "postgresql://localhost/mydb",
            "postgresql://myhost:5432/testdb",
        ]

        for url in urls:
            redacted = redact_url_credentials(url)
            assert redacted == url


class TestRateLimitValidation:
    """Property tests for rate limit configuration validation.

    **Feature: core-code-review**
    **Validates: Requirements 1.4**
    """

    @given(
        number=st.integers(min_value=1, max_value=10000),
        unit=st.sampled_from(["second", "minute", "hour", "day"]),
    )
    @settings(max_examples=100)
    def test_valid_rate_limits_accepted(self, number: int, unit: str):
        """For any valid rate limit format, validation SHALL pass."""
        rate_limit = f"{number}/{unit}"

        with patch.dict(os.environ, {
            "SECURITY__SECRET_KEY": "a" * 32,
            "SECURITY__RATE_LIMIT": rate_limit,
        }):
            settings_obj = SecuritySettings()
            assert settings_obj.rate_limit == rate_limit

    def test_invalid_rate_limits_rejected(self):
        """For any invalid rate limit format, validation SHALL raise ValueError."""
        invalid_rates = [
            "invalid",
            "100",
            "minute/100",
            "100/invalid",
            "abc/second",
        ]

        for invalid_rate in invalid_rates:
            with patch.dict(os.environ, {
                "SECURITY__SECRET_KEY": "a" * 32,
                "SECURITY__RATE_LIMIT": invalid_rate,
            }):
                with pytest.raises(ValidationError):
                    SecuritySettings()


class TestDatabaseSettingsSafeRepr:
    """Tests for DatabaseSettings safe representation."""

    def test_repr_does_not_expose_password(self):
        """__repr__ SHALL NOT expose database password."""
        settings_obj = DatabaseSettings(
            url="postgresql://user:secretpassword@localhost/mydb"
        )
        repr_str = repr(settings_obj)

        assert "secretpassword" not in repr_str
        assert "[REDACTED]" in repr_str
