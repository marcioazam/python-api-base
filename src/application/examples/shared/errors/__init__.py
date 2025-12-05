"""Shared errors for examples.

**Feature: example-system-demo**
"""

from application.examples.shared.errors.errors import (
    NotFoundError,
    UseCaseError,
    ValidationError,
)

__all__ = [
    "NotFoundError",
    "UseCaseError",
    "ValidationError",
]
