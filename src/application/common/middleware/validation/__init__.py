"""Validation middleware for CQRS command bus.

Re-exports all validation classes for backward compatibility.

**Feature: application-layer-code-review-2025**
**Refactored: Split into separate files for one-class-per-file compliance**
"""

from application.common.errors import ValidationError
from application.common.middleware.validation.base import CompositeValidator, Validator
from application.common.middleware.validation.middleware import ValidationMiddleware
from application.common.middleware.validation.validators import (
    RangeValidator,
    RequiredFieldValidator,
    StringLengthValidator,
)

__all__ = [
    # Base
    "Validator",
    "CompositeValidator",
    # Middleware
    "ValidationMiddleware",
    # Validators
    "RequiredFieldValidator",
    "StringLengthValidator",
    "RangeValidator",
    # Error (re-exported from exceptions)
    "ValidationError",
]
