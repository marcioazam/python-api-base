"""Domain type definitions.

Contains repository and security types.

**Feature: core-types-restructuring-2025**
"""

from core.types.domain.repository_types import (
    ApiResult,
    CRUDRepository,
    ErrorResult,
    PaginatedResult,
    ReadOnlyRepository,
    ReadOnlyUseCase,
    StandardUseCase,
    WriteOnlyRepository,
)
from core.types.domain.security_types import JWTToken, Password, SecurePassword

__all__ = [
    # Repository Types
    "ApiResult",
    "CRUDRepository",
    "ErrorResult",
    "PaginatedResult",
    "ReadOnlyRepository",
    "ReadOnlyUseCase",
    "StandardUseCase",
    "WriteOnlyRepository",
    # Security Types
    "JWTToken",
    "Password",
    "SecurePassword",
]
