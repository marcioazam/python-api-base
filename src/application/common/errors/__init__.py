"""Common exceptions for application layer.

Organized into subpackages by error category:
- base/: Base application error and handler not found
- validation/: Validation errors
- not_found/: Entity not found errors
- conflict/: Resource conflict errors
- auth/: Authentication and authorization errors

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.errors.auth import (
    ForbiddenError,
    UnauthorizedError,
)
from application.common.errors.base import (
    ApplicationError,
    HandlerNotFoundError,
)
from application.common.errors.conflict import ConflictError
from application.common.errors.not_found import NotFoundError
from application.common.errors.validation import ValidationError

__all__ = [
    "ApplicationError",
    "ConflictError",
    "ForbiddenError",
    "HandlerNotFoundError",
    "NotFoundError",
    "UnauthorizedError",
    "ValidationError",
]
