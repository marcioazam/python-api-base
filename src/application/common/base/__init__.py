"""Base classes for application layer.

Provides foundational abstractions:
- DTOs: Generic API response types
- Mapper: Entity-DTO conversion
- UseCase: Base use case pattern
- Exceptions: Application-level errors
"""

from application.common.base.dto import ApiResponse, PaginatedResponse, ProblemDetail
from application.common.base.mapper import IMapper, Mapper
from application.common.base.use_case import BaseUseCase
from application.common.base.exceptions import (
    ApplicationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)

__all__ = [
    # DTOs
    "ApiResponse",
    "PaginatedResponse",
    "ProblemDetail",
    # Mapper
    "IMapper",
    "Mapper",
    # UseCase
    "BaseUseCase",
    # Exceptions
    "ApplicationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
]
