"""Generic error classes with PEP 695 type parameters.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.shared.utils.ids import generate_ulid


@dataclass(frozen=True, slots=True)
class ErrorContext[T]:
    """Generic error context with typed payload.

    Type Parameters:
        T: The type of additional context data.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 9.4, 9.5**
    """

    correlation_id: str = field(default_factory=generate_ulid)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context_data: T | None = None
    request_path: str | None = None
    operation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "context_data": self.context_data,
            "request_path": self.request_path,
            "operation": self.operation,
        }


class DomainError[T](Exception):
    """Generic domain error with typed context.

    Type Parameters:
        T: The type of domain context data.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 9.1**

    Example:
        >>> class UserContext:
        ...     user_id: str
        ...     action: str
        >>> raise DomainError[UserContext](
        ...     message="User action failed",
        ...     context=UserContext(user_id="123", action="update"),
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "DOMAIN_ERROR",
        context: T | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.context = context
        self._cause = cause
        super().__init__(message)
        if cause:
            self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary."""
        result = {
            "type": "DomainError",
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }
        if self._cause:
            result["cause"] = str(self._cause)
        return result


class ApplicationError[T](Exception):
    """Generic application error with operation context.

    Type Parameters:
        T: The type of operation context data.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 9.2**

    Example:
        >>> @dataclass
        ... class OperationContext:
        ...     use_case: str
        ...     input_data: dict
        >>> raise ApplicationError[OperationContext](
        ...     message="Use case failed",
        ...     operation="CreateUser",
        ...     context=OperationContext(use_case="CreateUser", input_data={}),
        ... )
    """

    def __init__(
        self,
        message: str,
        operation: str,
        error_code: str = "APPLICATION_ERROR",
        context: T | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.message = message
        self.operation = operation
        self.error_code = error_code
        self.context = context
        self._cause = cause
        super().__init__(message)
        if cause:
            self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary."""
        result = {
            "type": "ApplicationError",
            "message": self.message,
            "operation": self.operation,
            "error_code": self.error_code,
            "context": self.context,
        }
        if self._cause:
            result["cause"] = str(self._cause)
        return result


class InfrastructureError[T](Exception):
    """Generic infrastructure error with service context.

    Type Parameters:
        T: The type of service context data.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 9.3**

    Example:
        >>> @dataclass
        ... class DatabaseContext:
        ...     connection_string: str
        ...     query: str
        >>> raise InfrastructureError[DatabaseContext](
        ...     message="Database connection failed",
        ...     service="PostgreSQL",
        ...     context=DatabaseContext(connection_string="...", query="SELECT..."),
        ... )
    """

    def __init__(
        self,
        message: str,
        service: str,
        error_code: str = "INFRASTRUCTURE_ERROR",
        context: T | None = None,
        cause: Exception | None = None,
        recoverable: bool = True,
    ) -> None:
        self.message = message
        self.service = service
        self.error_code = error_code
        self.context = context
        self._cause = cause
        self.recoverable = recoverable
        super().__init__(message)
        if cause:
            self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary."""
        result = {
            "type": "InfrastructureError",
            "message": self.message,
            "service": self.service,
            "error_code": self.error_code,
            "context": self.context,
            "recoverable": self.recoverable,
        }
        if self._cause:
            result["cause"] = str(self._cause)
        return result


def map_error[TFrom, TTo](
    error: DomainError[TFrom] | ApplicationError[TFrom] | InfrastructureError[TFrom],
    mapper: Callable[[TFrom | None], TTo | None],
) -> DomainError[TTo] | ApplicationError[TTo] | InfrastructureError[TTo]:
    """Map error context from one type to another.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 9.4**

    Args:
        error: Original error with context type TFrom.
        mapper: Function to convert context from TFrom to TTo.

    Returns:
        New error with mapped context type TTo.
    """

    new_context = mapper(error.context) if error.context else None

    if isinstance(error, DomainError):
        return DomainError[TTo](
            message=error.message,
            error_code=error.error_code,
            context=new_context,
            cause=error._cause,
        )
    if isinstance(error, ApplicationError):
        return ApplicationError[TTo](
            message=error.message,
            operation=error.operation,
            error_code=error.error_code,
            context=new_context,
            cause=error._cause,
        )
    return InfrastructureError[TTo](
        message=error.message,
        service=error.service,
        error_code=error.error_code,
        context=new_context,
        cause=error._cause,
        recoverable=error.recoverable,
    )
