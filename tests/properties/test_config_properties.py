"""Property-based tests for configuration validation.

**Feature: architecture-restructuring-2025, Property 1: Configuration Loading from Environment**
**Validates: Requirements 1.1**
"""

import os
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

try:
    from core.config.settings import SecuritySettings, Settings, DatabaseSettings, ObservabilitySettings
except ImportError:
    from core.config import SecuritySettings, Settings


class TestConfigValidation:
    """Property tests for configuration validation."""

    @settings(max_examples=20, deadline=None)
    @given(
        secret_key=st.text(
            min_size=0,
            max_size=31,
            alphabet=st.characters(blacklist_characters="\x00"),
        ),
    )
    def test_short_secret_key_fails_validation(self, secret_key: str) -> None:
        """
        **Feature: generic-fastapi-crud, Property 18: Missing Config Fails Fast**

        For any secret key shorter than 32 characters, Settings SHALL raise
        a ValidationError with a descriptive message at startup.
        """
        with patch.dict(os.environ, {"SECURITY__SECRET_KEY": secret_key}, clear=False):
            with pytest.raises(ValidationError) as exc_info:
                SecuritySettings()

            # Verify error is descriptive
            errors = exc_info.value.errors()
            assert len(errors) > 0
            assert any("secret_key" in str(e.get("loc", "")) for e in errors)

    @settings(max_examples=20)
    @given(
        secret_key=st.text(min_size=32, max_size=64, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_valid_secret_key_passes_validation(self, secret_key: str) -> None:
        """
        For any secret key with 32+ characters, SecuritySettings SHALL
        successfully validate without raising errors.
        """
        with patch.dict(os.environ, {"SECURITY__SECRET_KEY": secret_key}, clear=False):
            settings_obj = SecuritySettings()
            assert settings_obj.secret_key.get_secret_value() == secret_key

    @settings(max_examples=10)
    @given(
        log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    )
    def test_valid_log_levels_pass_validation(self, log_level: str) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 1: Configuration Loading from Environment**
        
        For any valid log level, ObservabilitySettings SHALL accept the value.
        **Validates: Requirements 1.1**
        """
        try:
            from core.config.settings import ObservabilitySettings
        except ImportError:
            from core.config import ObservabilitySettings

        with patch.dict(
            os.environ, {"OBSERVABILITY__LOG_LEVEL": log_level}, clear=False
        ):
            settings_obj = ObservabilitySettings()
            assert settings_obj.log_level == log_level

    @settings(max_examples=10)
    @given(
        log_level=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))).filter(
            lambda x: x not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ),
    )
    def test_invalid_log_levels_fail_validation(self, log_level: str) -> None:
        """
        For any invalid log level, ObservabilitySettings SHALL raise
        a ValidationError.
        """
        try:
            from core.config.settings import ObservabilitySettings
        except ImportError:
            from core.config import ObservabilitySettings

        with patch.dict(
            os.environ, {"OBSERVABILITY__LOG_LEVEL": log_level}, clear=False
        ):
            with pytest.raises(ValidationError):
                ObservabilitySettings()

    def test_missing_required_secret_key_fails(self) -> None:
        """
        When SECURITY__SECRET_KEY is not set, Settings SHALL fail fast
        with a descriptive error message.
        """
        # Clear the secret key from environment
        env = {k: v for k, v in os.environ.items() if "SECRET_KEY" not in k}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            errors = exc_info.value.errors()
            assert len(errors) > 0
            # Check that error mentions the missing field
            error_locs = [str(e.get("loc", "")) for e in errors]
            assert any("secret_key" in loc for loc in error_locs)

    @settings(max_examples=10)
    @given(
        pool_size=st.integers(min_value=1, max_value=100),
        max_overflow=st.integers(min_value=0, max_value=100),
    )
    def test_valid_database_pool_settings(
        self, pool_size: int, max_overflow: int
    ) -> None:
        """
        For any valid pool_size (1-100) and max_overflow (0-100),
        DatabaseSettings SHALL accept the values.
        """
        try:
            from core.config.settings import DatabaseSettings
        except ImportError:
            from core.config import DatabaseSettings

        with patch.dict(
            os.environ,
            {
                "DATABASE__POOL_SIZE": str(pool_size),
                "DATABASE__MAX_OVERFLOW": str(max_overflow),
            },
            clear=False,
        ):
            settings_obj = DatabaseSettings()
            assert settings_obj.pool_size == pool_size
            assert settings_obj.max_overflow == max_overflow

    @settings(max_examples=10)
    @given(
        pool_size=st.integers(max_value=0) | st.integers(min_value=101, max_value=200),
    )
    def test_invalid_pool_size_fails(self, pool_size: int) -> None:
        """
        For any pool_size outside 1-100 range, DatabaseSettings SHALL
        raise a ValidationError.
        """
        from core.config import DatabaseSettings

        with patch.dict(
            os.environ,
            {"DATABASE__POOL_SIZE": str(pool_size)},
            clear=False,
        ):
            with pytest.raises(ValidationError):
                DatabaseSettings()
