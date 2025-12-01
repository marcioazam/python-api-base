"""CLI exception hierarchy.

Provides structured exceptions for CLI error handling.
"""

from typing import Final


class CLIError(Exception):
    """Base CLI error."""

    exit_code: Final[int] = 1

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class ValidationError(CLIError):
    """Validation error for CLI inputs."""

    exit_code: Final[int] = 2


class CLITimeoutError(CLIError):
    """Timeout error for CLI operations."""

    exit_code: Final[int] = 3


class InvalidFieldError(CLIError):
    """Invalid field definition error."""

    exit_code: Final[int] = 4
