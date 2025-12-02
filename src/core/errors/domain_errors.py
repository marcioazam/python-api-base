"""Compatibility alias for core.errors.base.domain_errors."""

from core.errors.base.domain_errors import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    ConflictError,
    EntityNotFoundError,
    ErrorContext,
    RateLimitExceededError,
    ValidationError,
)

__all__ = [
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessRuleViolationError",
    "ConflictError",
    "EntityNotFoundError",
    "ErrorContext",
    "RateLimitExceededError",
    "ValidationError",
]
