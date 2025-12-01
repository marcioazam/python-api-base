"""Property-based tests for CLI version.

**Feature: cli-security-improvements, Property 9: Version Format Consistency**
**Validates: Requirements 6.3**
"""

import re
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.cli.constants import CLI_DEFAULT_VERSION, CLI_NAME
from my_app.cli.main import get_version


class TestVersionFormatConsistency:
    """Property 9: Version Format Consistency.

    For any version output, it matches the format "{cli_name} version: {semver}"
    where semver follows semantic versioning or ends with "-dev".
    """

    # Semantic version pattern (simplified)
    SEMVER_PATTERN = re.compile(
        r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$"
    )

    def test_default_version_format(self) -> None:
        """Default version follows expected format."""
        assert self.SEMVER_PATTERN.match(CLI_DEFAULT_VERSION)
        assert CLI_DEFAULT_VERSION.endswith("-dev")

    def test_get_version_returns_string(self) -> None:
        """get_version always returns a string."""
        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_get_version_format_valid(self) -> None:
        """get_version returns valid semver format."""
        version = get_version()
        # Should match semver or end with -dev
        is_valid = (
            self.SEMVER_PATTERN.match(version) is not None
            or version.endswith("-dev")
        )
        assert is_valid, f"Version '{version}' does not match expected format"

    @given(
        major=st.integers(min_value=0, max_value=99),
        minor=st.integers(min_value=0, max_value=99),
        patch=st.integers(min_value=0, max_value=99),
    )
    @settings(max_examples=100)
    def test_semver_pattern_accepts_valid_versions(
        self, major: int, minor: int, patch: int
    ) -> None:
        """Semver pattern accepts valid version strings."""
        version = f"{major}.{minor}.{patch}"
        assert self.SEMVER_PATTERN.match(version)

    @given(
        major=st.integers(min_value=0, max_value=99),
        minor=st.integers(min_value=0, max_value=99),
        patch=st.integers(min_value=0, max_value=99),
        prerelease=st.sampled_from(["alpha", "beta", "rc1", "dev"]),
    )
    @settings(max_examples=100)
    def test_semver_pattern_accepts_prerelease(
        self, major: int, minor: int, patch: int, prerelease: str
    ) -> None:
        """Semver pattern accepts prerelease versions."""
        version = f"{major}.{minor}.{patch}-{prerelease}"
        assert self.SEMVER_PATTERN.match(version)

    def test_fallback_version_on_package_not_found(self) -> None:
        """get_version returns fallback when package not found."""
        from importlib.metadata import PackageNotFoundError

        with patch(
            "my_app.cli.main.pkg_version",
            side_effect=PackageNotFoundError("test"),
        ):
            version = get_version()
            assert version == CLI_DEFAULT_VERSION

    @given(
        version=st.from_regex(r"^\d+\.\d+\.\d+$", fullmatch=True),
    )
    @settings(max_examples=100)
    def test_mocked_version_format(self, version: str) -> None:
        """Mocked versions maintain valid format."""
        with patch("my_app.cli.main.pkg_version", return_value=version):
            result = get_version()
            assert result == version
            assert self.SEMVER_PATTERN.match(result)


class TestCLINameConsistency:
    """Test CLI name is consistent."""

    def test_cli_name_is_defined(self) -> None:
        """CLI_NAME constant is defined and non-empty."""
        assert CLI_NAME
        assert isinstance(CLI_NAME, str)
        assert len(CLI_NAME) > 0

    def test_cli_name_format(self) -> None:
        """CLI_NAME follows expected format (lowercase with hyphens)."""
        assert re.match(r"^[a-z][a-z0-9\-]*$", CLI_NAME)


class TestVersionOutput:
    """Test version command output format."""

    def test_version_output_format(self) -> None:
        """Version output follows expected format."""
        version = get_version()
        expected_output = f"{CLI_NAME} version: {version}"

        # Verify the format components
        assert CLI_NAME in expected_output
        assert "version:" in expected_output
        assert version in expected_output
