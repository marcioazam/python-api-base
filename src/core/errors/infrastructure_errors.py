"""Compatibility alias for core.errors.base.infrastructure_errors."""

from core.errors.base.infrastructure_errors import (
    InfrastructureError,
    DatabaseError,
    ExternalServiceError,
)

__all__ = [
    "InfrastructureError",
    "DatabaseError",
    "ExternalServiceError",
]
