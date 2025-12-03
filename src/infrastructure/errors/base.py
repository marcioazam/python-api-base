"""Base infrastructure exception.

**Feature: infrastructure-code-review**
**Validates: Requirements 8.2, 10.3**
"""

from __future__ import annotations

from typing import Any


class InfrastructureError(Exception):
    """Base exception for all infrastructure errors.

    All infrastructure exceptions should inherit from this class
    to enable consistent error handling and filtering.

    Attributes:
        message: Human-readable error message.
        details: Additional context about the error.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize infrastructure error.

        Args:
            message: Human-readable error message.
            details: Additional context about the error.
        """
        self.message = message
        self.details = details or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format message with details."""
        if not self.details:
            return self.message
        details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
        return f"{self.message} ({details_str})"
