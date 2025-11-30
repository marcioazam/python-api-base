"""CLI-specific exceptions.

**Feature: cli-security-improvements, Task 1.2: Exceptions Module**
**Validates: Requirements 3.1, 3.4, 3.5**
"""

from typing import Final

from my_api.cli.constants import EXIT_ERROR, EXIT_TIMEOUT


class CLIError(Exception):
    """Base exception for CLI errors.

    All CLI-specific exceptions should inherit from this class.
    Provides standardized exit code handling.
    """

    exit_code: int = EXIT_ERROR

    def __init__(self, message: str, exit_code: int | None = None) -> None:
        """Initialize CLI error.

        Args:
            message: Human-readable error message.
            exit_code: Optional exit code override.
        """
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class ValidationError(CLIError):
    """Input validation error.

    Raised when user input fails validation checks.
    Exit code: 1 (general error)
    """

    pass


class InvalidRevisionError(ValidationError):
    """Invalid database revision format."""

    def __init__(self, revision: str) -> None:
        super().__init__(f"Invalid revision format: {revision}")
        self.revision = revision


class InvalidEntityNameError(ValidationError):
    """Invalid entity name format or length."""

    def __init__(self, name: str, reason: str = "invalid format") -> None:
        super().__init__(f"Invalid entity name '{name}': {reason}")
        self.name = name
        self.reason = reason


class InvalidPathError(ValidationError):
    """Invalid or unsafe path."""

    def __init__(self, path: str, reason: str = "path traversal detected") -> None:
        super().__init__(f"Invalid path '{path}': {reason}")
        self.path = path
        self.reason = reason


class InvalidFieldError(ValidationError):
    """Invalid field definition."""

    def __init__(self, field: str, reason: str = "invalid format") -> None:
        super().__init__(f"Invalid field '{field}': {reason}")
        self.field = field
        self.reason = reason


class InvalidCommandError(ValidationError):
    """Invalid command not in whitelist."""

    def __init__(self, command: str, allowed: frozenset[str]) -> None:
        allowed_str = ", ".join(sorted(allowed))
        super().__init__(f"Invalid command '{command}'. Allowed: {allowed_str}")
        self.command = command
        self.allowed = allowed


class CommandError(CLIError):
    """Command execution error.

    Raised when a subprocess command fails.
    Exit code: 1 (general error)
    """

    def __init__(self, message: str, return_code: int | None = None) -> None:
        super().__init__(message)
        self.return_code = return_code


class AlembicError(CommandError):
    """Alembic command execution error."""

    pass


class PytestError(CommandError):
    """Pytest command execution error."""

    pass


class CLITimeoutError(CLIError):
    """Command timeout error.

    Raised when a subprocess exceeds the configured timeout.
    Exit code: 124 (standard timeout exit code)
    """

    exit_code: Final[int] = EXIT_TIMEOUT

    def __init__(self, command: str, timeout: int) -> None:
        super().__init__(f"Command timed out after {timeout}s: {command}")
        self.command = command
        self.timeout = timeout
