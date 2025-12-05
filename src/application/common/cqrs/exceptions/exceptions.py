"""CQRS exceptions module.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 2.1**
"""


class CQRSError(Exception):
    """Base exception for CQRS errors."""


class HandlerNotFoundError(CQRSError):
    """Raised when no handler is registered for a command/query type."""

    def __init__(self, command_type: type) -> None:
        self.command_type = command_type
        super().__init__(f"No handler registered for {command_type.__name__}")


class HandlerAlreadyRegisteredError(CQRSError):
    """Raised when trying to register a handler that already exists."""

    def __init__(self, command_type: type) -> None:
        self.command_type = command_type
        super().__init__(f"Handler already registered for {command_type.__name__}")


class MiddlewareError(CQRSError):
    """Raised when middleware execution fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
