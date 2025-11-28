"""Annotated types for inline validation using PEP 593.

This module provides reusable type aliases with built-in validation
constraints using `typing.Annotated` and Pydantic's `Field`.

**When to use Annotated types:**
- Pure Pydantic models (BaseModel subclasses)
- API request/response DTOs that don't use SQLModel
- Domain value objects
- Configuration models

**When NOT to use Annotated types:**
- SQLModel entities with `table=True` (use SQLField constraints instead)
- SQLModel DTOs that inherit from SQLModel (use SQLField constraints)

Usage with pure Pydantic:
    from pydantic import BaseModel
    from my_api.shared.types import ULID, Email, NonEmptyStr, PositiveInt

    class UserDTO(BaseModel):
        id: ULID
        email: Email
        name: NonEmptyStr
        age: PositiveInt

Usage with SQLModel (use SQLField instead):
    from sqlmodel import SQLModel, Field as SQLField

    class Item(SQLModel, table=True):
        name: str = SQLField(min_length=1, max_length=255)
        price: float = SQLField(gt=0)
"""

from typing import Annotated

from pydantic import Field, StringConstraints

# =============================================================================
# ID Types
# =============================================================================

ULID = Annotated[
    str,
    StringConstraints(
        min_length=26,
        max_length=26,
        pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$",
    ),
    Field(description="ULID identifier (26 characters, Crockford Base32)"),
]
"""ULID string with validation (26 chars, Crockford Base32)."""

UUID = Annotated[
    str,
    StringConstraints(
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    ),
    Field(description="UUID identifier (36 characters with hyphens)"),
]
"""UUID string with validation (36 chars with hyphens)."""

# =============================================================================
# String Types
# =============================================================================

NonEmptyStr = Annotated[
    str,
    StringConstraints(min_length=1, strip_whitespace=True),
    Field(description="Non-empty string (whitespace stripped)"),
]
"""Non-empty string with whitespace stripping."""

TrimmedStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    Field(description="String with whitespace stripped"),
]
"""String with leading/trailing whitespace stripped."""

ShortStr = Annotated[
    str,
    StringConstraints(max_length=100, strip_whitespace=True),
    Field(description="Short string (max 100 chars)"),
]
"""Short string limited to 100 characters."""

MediumStr = Annotated[
    str,
    StringConstraints(max_length=500, strip_whitespace=True),
    Field(description="Medium string (max 500 chars)"),
]
"""Medium string limited to 500 characters."""

LongStr = Annotated[
    str,
    StringConstraints(max_length=5000),
    Field(description="Long string (max 5000 chars)"),
]
"""Long string limited to 5000 characters."""

Slug = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
    Field(description="URL-safe slug (lowercase, hyphens)"),
]
"""URL-safe slug (lowercase letters, numbers, hyphens)."""

# =============================================================================
# Contact Types
# =============================================================================

Email = Annotated[
    str,
    StringConstraints(
        min_length=5,
        max_length=254,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    ),
    Field(description="Email address"),
]
"""Email address with basic validation."""

PhoneNumber = Annotated[
    str,
    StringConstraints(
        min_length=10,
        max_length=20,
        pattern=r"^\+?[0-9\s\-\(\)]+$",
    ),
    Field(description="Phone number (international format supported)"),
]
"""Phone number with international format support."""

# =============================================================================
# Numeric Types
# =============================================================================

PositiveInt = Annotated[
    int,
    Field(gt=0, description="Positive integer (> 0)"),
]
"""Positive integer greater than zero."""

NonNegativeInt = Annotated[
    int,
    Field(ge=0, description="Non-negative integer (>= 0)"),
]
"""Non-negative integer (zero or positive)."""

PositiveFloat = Annotated[
    float,
    Field(gt=0, description="Positive float (> 0)"),
]
"""Positive float greater than zero."""

NonNegativeFloat = Annotated[
    float,
    Field(ge=0, description="Non-negative float (>= 0)"),
]
"""Non-negative float (zero or positive)."""

Percentage = Annotated[
    float,
    Field(ge=0, le=100, description="Percentage value (0-100)"),
]
"""Percentage value between 0 and 100."""

# =============================================================================
# Pagination Types
# =============================================================================

PageNumber = Annotated[
    int,
    Field(ge=1, le=10000, description="Page number (1-indexed)"),
]
"""Page number for pagination (1-indexed, max 10000)."""

PageSize = Annotated[
    int,
    Field(ge=1, le=100, description="Items per page (1-100)"),
]
"""Page size for pagination (1-100 items)."""

# =============================================================================
# Security Types
# =============================================================================

Password = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128),
    Field(description="Password (8-128 characters)"),
]
"""Password with minimum length requirement."""

SecurePassword = Annotated[
    str,
    StringConstraints(
        min_length=12,
        max_length=128,
        pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$",
    ),
    Field(description="Secure password (12+ chars, mixed case, number, special)"),
]
"""Secure password with complexity requirements."""

JWTToken = Annotated[
    str,
    StringConstraints(
        min_length=20,
        pattern=r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
    ),
    Field(description="JWT token (header.payload.signature)"),
]
"""JWT token with basic format validation."""

# =============================================================================
# URL Types
# =============================================================================

HttpUrl = Annotated[
    str,
    StringConstraints(
        min_length=10,
        max_length=2048,
        pattern=r"^https?://[^\s]+$",
    ),
    Field(description="HTTP/HTTPS URL"),
]
"""HTTP or HTTPS URL."""

# =============================================================================
# Code/Technical Types
# =============================================================================

VersionStr = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=20,
        pattern=r"^v?\d+(\.\d+)*(-[a-zA-Z0-9]+)?$",
    ),
    Field(description="Version string (e.g., v1.0.0, 2.1.0-beta)"),
]
"""Semantic version string."""

ISODateStr = Annotated[
    str,
    StringConstraints(
        min_length=10,
        max_length=30,
        pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$",
    ),
    Field(description="ISO 8601 date/datetime string"),
]
"""ISO 8601 formatted date or datetime string."""


# =============================================================================
# Type Aliases (PEP 695)
# =============================================================================
# Using PEP 695 `type` statement (Python 3.12+) for cleaner type alias definitions.
# This is the modern replacement for `TypeAlias` from typing module.

# -----------------------------------------------------------------------------
# Filter and Query Type Aliases
# -----------------------------------------------------------------------------

type FilterDict = dict[str, "Any"]
"""Type alias for filter dictionary used in repository queries."""

type SortOrder = "Literal['asc', 'desc']"
"""Type alias for sort order in queries."""

type QueryParams = dict[str, str | int | float | bool | None]
"""Type alias for URL query parameters."""

type Headers = dict[str, str]
"""Type alias for HTTP headers."""

# -----------------------------------------------------------------------------
# JSON Type Aliases
# -----------------------------------------------------------------------------

type JSONPrimitive = str | int | float | bool | None
"""Type alias for JSON primitive values."""

type JSONValue = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
"""Type alias for any JSON value."""

type JSONObject = dict[str, JSONValue]
"""Type alias for JSON object."""

type JSONArray = list[JSONValue]
"""Type alias for JSON array."""

# -----------------------------------------------------------------------------
# Repository Type Aliases
# -----------------------------------------------------------------------------

type CRUDRepository[T, CreateT, UpdateT] = "IRepository[T, CreateT, UpdateT]"
"""Type alias for generic CRUD repository with full operations."""

type ReadOnlyRepository[T] = "IRepository[T, None, None]"
"""Type alias for read-only repository (no create/update)."""

type WriteOnlyRepository[T, CreateT] = "IRepository[T, CreateT, None]"
"""Type alias for write-only repository (create only, no update)."""

# -----------------------------------------------------------------------------
# Use Case Type Aliases
# -----------------------------------------------------------------------------

type StandardUseCase[T, CreateDTO, UpdateDTO, ResponseDTO] = (
    "BaseUseCase[T, CreateDTO, UpdateDTO, ResponseDTO]"
)
"""Type alias for standard CRUD use case with all operations."""

type ReadOnlyUseCase[T, ResponseDTO] = "BaseUseCase[T, None, None, ResponseDTO]"
"""Type alias for read-only use case."""

# -----------------------------------------------------------------------------
# Response Type Aliases
# -----------------------------------------------------------------------------

type ApiResult[T] = "ApiResponse[T]"
"""Type alias for API response wrapper."""

type PaginatedResult[T] = "PaginatedResponse[T]"
"""Type alias for paginated response."""

type ErrorResult = "ProblemDetail"
"""Type alias for error response (RFC 7807)."""

# -----------------------------------------------------------------------------
# Result Pattern Type Aliases
# -----------------------------------------------------------------------------

type Success[T] = "Ok[T]"
"""Type alias for successful result."""

type Failure[E] = "Err[E]"
"""Type alias for failed result."""

type OperationResult[T, E] = "Result[T, E]"
"""Type alias for operation result (success or failure)."""

type VoidResult[E] = "Result[None, E]"
"""Type alias for void operation result (no return value on success)."""

# -----------------------------------------------------------------------------
# Callback Type Aliases
# -----------------------------------------------------------------------------

type AsyncCallback[T] = "Callable[..., Awaitable[T]]"
"""Type alias for async callback function."""

type SyncCallback[T] = "Callable[..., T]"
"""Type alias for sync callback function."""

type EventCallback = "Callable[[DomainEvent], Awaitable[None] | None]"
"""Type alias for event handler callback."""

type Middleware = "Callable[[Request, Callable], Awaitable[Response]]"
"""Type alias for ASGI middleware callable."""

# -----------------------------------------------------------------------------
# Entity and ID Type Aliases
# -----------------------------------------------------------------------------

type EntityId = str | int
"""Type alias for entity identifier (ULID string or integer)."""

type Timestamp = "datetime"
"""Type alias for timestamp fields."""

# -----------------------------------------------------------------------------
# Specification Type Aliases
# -----------------------------------------------------------------------------

type Spec[T] = "Specification[T]"
"""Type alias for specification pattern."""

type CompositeSpec[T] = "Specification[T]"
"""Type alias for composite specification (AND/OR/NOT)."""
