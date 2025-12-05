"""Repository and use case type aliases using PEP 695 type statement.

**Feature: core-types-split-2025**

Note: Forward references are intentional for types defined in other modules.
"""
# ruff: noqa: F821

__all__ = [
    # Response
    "ApiResult",
    # Repository
    "CRUDRepository",
    "ErrorResult",
    "PaginatedResult",
    "ReadOnlyRepository",
    # Use Case
    "ReadOnlyUseCase",
    "StandardUseCase",
    "WriteOnlyRepository",
]

# =============================================================================
# Repository Type Aliases
# =============================================================================

type CRUDRepository[T, CreateT, UpdateT] = "IRepository[T, CreateT, UpdateT]"
"""Type alias for generic CRUD repository with full operations."""

type ReadOnlyRepository[T] = "IRepository[T, None, None]"
"""Type alias for read-only repository (no create/update)."""

type WriteOnlyRepository[T, CreateT] = "IRepository[T, CreateT, None]"
"""Type alias for write-only repository (create only, no update)."""

# =============================================================================
# Use Case Type Aliases
# =============================================================================

type StandardUseCase[T, CreateDTO, UpdateDTO, ResponseDTO] = (
    "BaseUseCase[T, CreateDTO, UpdateDTO, ResponseDTO]"
)
"""Type alias for standard CRUD use case with all operations."""

type ReadOnlyUseCase[T, ResponseDTO] = "BaseUseCase[T, None, None, ResponseDTO]"
"""Type alias for read-only use case."""

# =============================================================================
# Response Type Aliases
# =============================================================================

type ApiResult[T] = "ApiResponse[T]"
"""Type alias for API response wrapper."""

type PaginatedResult[T] = "PaginatedResponse[T]"
"""Type alias for paginated response."""

type ErrorResult = "ProblemDetail"
"""Type alias for error response (RFC 7807)."""
