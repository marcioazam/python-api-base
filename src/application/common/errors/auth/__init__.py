"""Authentication and authorization errors.

Provides auth-related exception types.

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.errors.auth.forbidden_error import ForbiddenError
from application.common.errors.auth.unauthorized_error import UnauthorizedError

__all__ = [
    "ForbiddenError",
    "UnauthorizedError",
]
