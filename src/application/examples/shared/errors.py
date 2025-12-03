"""Error classes for Example system.

Re-exports from application.common.base.exceptions for consistency.
Provides backward compatibility while using unified error hierarchy.

**Feature: example-system-demo**
**Refactored: 2025 - Unified with application.common errors**
"""

from typing import Any

from application.common.base.exceptions import (
    ApplicationError,
    NotFoundError as BaseNotFoundError,
    ValidationError as BaseValidationError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
)


# Re-export base errors for direct use
__all__ = [
    "UseCaseError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
]


class UseCaseError(ApplicationError):
    """Base error for use case failures.

    Extends ApplicationError for unified error handling.
    """

    def __init__(
        self,
        message: str,
        code: str = "USE_CASE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class NotFoundError(BaseNotFoundError):
    """Entity not found error.

    Wrapper for backward compatibility with existing code.
    """

    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(entity_type=entity, entity_id=entity_id)
        self.entity = entity


class ValidationError(BaseValidationError):
    """Validation error with optional field.

    Wrapper for backward compatibility with existing code.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        errors = [{"field": field, "message": message}] if field else []
        super().__init__(message=message, errors=errors)
        self.field = field
