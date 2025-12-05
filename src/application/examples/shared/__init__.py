"""Shared components for Example system.

Organized into subpackages:
- dtos/: Shared data transfer objects
- errors/: Shared error types

**Feature: example-system-demo**
"""

from application.examples.shared.dtos import MoneyDTO
from application.examples.shared.errors import (
    NotFoundError,
    UseCaseError,
    ValidationError,
)

__all__ = [
    # DTOs
    "MoneyDTO",
    # Errors
    "NotFoundError",
    "UseCaseError",
    "ValidationError",
]
