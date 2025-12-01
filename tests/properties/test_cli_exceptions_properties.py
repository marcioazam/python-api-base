"""Property-based tests for CLI exceptions.

**Feature: cli-security-improvements, Property 6: Exit Code Consistency**
**Validates: Requirements 3.3, 3.4, 3.5**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.cli.constants import EXIT_ERROR, EXIT_TIMEOUT
from my_app.cli.exceptions import (
    AlembicError,
    CLIError,
    CLITimeoutError,
    CommandError,
    InvalidCommandError,
    InvalidEntityNameError,
    InvalidFieldError,
    InvalidPathError,
    InvalidRevisionError,
    PytestError,
    ValidationError,
)


class TestExitCodeConsistency:
    """Property 6: Exit Code Consistency.

    For any CLI error type, the exit code returned matches the expected
    Unix convention (1 for general errors, 124 for timeout).
    """

    @given(message=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_cli_error_default_exit_code(self, message: str) -> None:
        """CLIError has default exit code of 1."""
        error = CLIError(message)
        assert error.exit_code == EXIT_ERROR

    @given(message=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_validation_error_exit_code(self, message: str) -> None:
        """ValidationError inherits exit code 1 from CLIError."""
        error = ValidationError(message)
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, CLIError)

    @given(message=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_command_error_exit_code(self, message: str) -> None:
        """CommandError has exit code 1."""
        error = CommandError(message)
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, CLIError)

    @given(
        command=st.text(min_size=1, max_size=50),
        timeout=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_timeout_error_exit_code(self, command: str, timeout: int) -> None:
        """CLITimeoutError has exit code 124."""
        error = CLITimeoutError(command, timeout)
        assert error.exit_code == EXIT_TIMEOUT
        assert isinstance(error, CLIError)

    @given(revision=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_invalid_revision_error_exit_code(self, revision: str) -> None:
        """InvalidRevisionError has exit code 1."""
        error = InvalidRevisionError(revision)
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, ValidationError)

    @given(name=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_invalid_entity_name_error_exit_code(self, name: str) -> None:
        """InvalidEntityNameError has exit code 1."""
        error = InvalidEntityNameError(name)
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, ValidationError)

    @given(path=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_invalid_path_error_exit_code(self, path: str) -> None:
        """InvalidPathError has exit code 1."""
        error = InvalidPathError(path)
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, ValidationError)

    @given(field=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_invalid_field_error_exit_code(self, field: str) -> None:
        """InvalidFieldError has exit code 1."""
        error = InvalidFieldError(field)
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, ValidationError)

    @given(command=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_invalid_command_error_exit_code(self, command: str) -> None:
        """InvalidCommandError has exit code 1."""
        error = InvalidCommandError(command, frozenset({"test"}))
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, ValidationError)

    @given(message=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_alembic_error_exit_code(self, message: str) -> None:
        """AlembicError has exit code 1."""
        error = AlembicError(message)
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, CommandError)

    @given(message=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_pytest_error_exit_code(self, message: str) -> None:
        """PytestError has exit code 1."""
        error = PytestError(message)
        assert error.exit_code == EXIT_ERROR
        assert isinstance(error, CommandError)


class TestExitCodeOverride:
    """Test that exit codes can be overridden when needed."""

    @given(
        message=st.text(min_size=1, max_size=100),
        exit_code=st.integers(min_value=0, max_value=255),
    )
    @settings(max_examples=100)
    def test_cli_error_custom_exit_code(self, message: str, exit_code: int) -> None:
        """CLIError accepts custom exit code."""
        error = CLIError(message, exit_code=exit_code)
        assert error.exit_code == exit_code


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_validation_errors_inherit_from_cli_error(self) -> None:
        """All validation errors inherit from CLIError."""
        validation_errors = [
            InvalidRevisionError("test"),
            InvalidEntityNameError("test"),
            InvalidPathError("test"),
            InvalidFieldError("test"),
            InvalidCommandError("test", frozenset({"allowed"})),
        ]
        for error in validation_errors:
            assert isinstance(error, CLIError)
            assert isinstance(error, ValidationError)

    def test_command_errors_inherit_from_cli_error(self) -> None:
        """All command errors inherit from CLIError."""
        command_errors = [
            CommandError("test"),
            AlembicError("test"),
            PytestError("test"),
        ]
        for error in command_errors:
            assert isinstance(error, CLIError)
            assert isinstance(error, CommandError)

    def test_timeout_error_inherits_from_cli_error(self) -> None:
        """Timeout error inherits from CLIError."""
        error = CLITimeoutError("test", 30)
        assert isinstance(error, CLIError)
