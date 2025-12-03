"""Application layer errors for use case and handler failures.

These errors are specific to the application layer (CQRS handlers, use cases).

**Feature: architecture-restructuring-2025**
**Validates: Requirements 1.7**
"""

from typing import Any

from core.errors.base.domain_errors import AppException, ErrorContext

__all__ = [
    "ApplicationError",
    "CommandHandlerError",
    "QueryHandlerError",
    "UseCaseError",
    "InvalidCommandError",
    "InvalidQueryError",
    "HandlerNotFoundError",
    "ConcurrencyError",
    "TransactionError",
]


class ApplicationError(AppException):
    """Base class for application layer errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "APPLICATION_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        context: ErrorContext | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
        )


class CommandHandlerError(ApplicationError):
    """Raised when a command handler fails."""

    def __init__(
        self,
        command_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"Command handler failed for {command_type}: {message}",
            error_code="COMMAND_HANDLER_ERROR",
            status_code=500,
            details={"command_type": command_type, **(details or {})},
        )


class QueryHandlerError(ApplicationError):
    """Raised when a query handler fails."""

    def __init__(
        self,
        query_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"Query handler failed for {query_type}: {message}",
            error_code="QUERY_HANDLER_ERROR",
            status_code=500,
            details={"query_type": query_type, **(details or {})},
        )


class UseCaseError(ApplicationError):
    """Raised when a use case fails."""

    def __init__(
        self,
        use_case: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"Use case '{use_case}' failed: {message}",
            error_code="USE_CASE_ERROR",
            status_code=500,
            details={"use_case": use_case, **(details or {})},
        )


class InvalidCommandError(ApplicationError):
    """Raised when a command is invalid."""

    def __init__(
        self,
        command_type: str,
        reason: str,
    ) -> None:
        super().__init__(
            message=f"Invalid command {command_type}: {reason}",
            error_code="INVALID_COMMAND",
            status_code=400,
            details={"command_type": command_type, "reason": reason},
        )


class InvalidQueryError(ApplicationError):
    """Raised when a query is invalid."""

    def __init__(
        self,
        query_type: str,
        reason: str,
    ) -> None:
        super().__init__(
            message=f"Invalid query {query_type}: {reason}",
            error_code="INVALID_QUERY",
            status_code=400,
            details={"query_type": query_type, "reason": reason},
        )


class HandlerNotFoundError(ApplicationError):
    """Raised when no handler is registered for a command/query."""

    def __init__(
        self,
        handler_type: str,
        message_type: str,
    ) -> None:
        super().__init__(
            message=f"No {handler_type} handler registered for {message_type}",
            error_code="HANDLER_NOT_FOUND",
            status_code=500,
            details={"handler_type": handler_type, "message_type": message_type},
        )


class ConcurrencyError(ApplicationError):
    """Raised when optimistic concurrency check fails."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(
            message=f"Concurrency conflict for {entity_type} {entity_id}",
            error_code="CONCURRENCY_ERROR",
            status_code=409,
            details={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class TransactionError(ApplicationError):
    """Raised when a transaction fails."""

    def __init__(
        self,
        operation: str,
        message: str,
    ) -> None:
        super().__init__(
            message=f"Transaction failed during {operation}: {message}",
            error_code="TRANSACTION_ERROR",
            status_code=500,
            details={"operation": operation},
        )
