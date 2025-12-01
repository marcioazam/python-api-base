"""Core type definitions using PEP 593 Annotated types and PEP 695 type aliases.

**Feature: core-types-split-2025**

Provides reusable type aliases with built-in validation constraints.
Refactored from monolithic types.py into focused modules.
"""

# ID Types
from .id_types import ULID, UUID

# String Types
from .string_types import (
    Email,
    HttpUrl,
    ISODateStr,
    LongStr,
    MediumStr,
    NonEmptyStr,
    PhoneNumber,
    ShortStr,
    Slug,
    TrimmedStr,
    VersionStr,
)

# Numeric Types
from .numeric_types import (
    NonNegativeFloat,
    NonNegativeInt,
    PageNumber,
    PageSize,
    Percentage,
    PositiveFloat,
    PositiveInt,
)

# Security Types
from .security_types import JWTToken, Password, SecurePassword

# JSON Type Aliases
from .json_types import (
    FilterDict,
    Headers,
    JSONArray,
    JSONObject,
    JSONPrimitive,
    JSONValue,
    QueryParams,
    SortOrder,
)

# Result Pattern and Callback Type Aliases
from .result_types import (
    AsyncCallback,
    CompositeSpec,
    EntityId,
    EventCallback,
    Failure,
    Middleware,
    OperationResult,
    Spec,
    Success,
    SyncCallback,
    Timestamp,
    VoidResult,
)

# Repository/UseCase Type Aliases
from .repository_types import (
    ApiResult,
    CRUDRepository,
    ErrorResult,
    PaginatedResult,
    ReadOnlyRepository,
    ReadOnlyUseCase,
    StandardUseCase,
    WriteOnlyRepository,
)

__all__ = [
    # ID Types
    "ULID",
    "UUID",
    "EntityId",
    # String Types
    "Email",
    "HttpUrl",
    "ISODateStr",
    "LongStr",
    "MediumStr",
    "NonEmptyStr",
    "PhoneNumber",
    "ShortStr",
    "Slug",
    "TrimmedStr",
    "VersionStr",
    # Numeric Types
    "NonNegativeFloat",
    "NonNegativeInt",
    "Percentage",
    "PositiveFloat",
    "PositiveInt",
    # Pagination Types
    "PageNumber",
    "PageSize",
    # Security Types
    "JWTToken",
    "Password",
    "SecurePassword",
    # JSON Type Aliases
    "JSONArray",
    "JSONObject",
    "JSONPrimitive",
    "JSONValue",
    # Filter/Query Type Aliases
    "FilterDict",
    "Headers",
    "QueryParams",
    "SortOrder",
    # Result Pattern Type Aliases
    "Failure",
    "OperationResult",
    "Success",
    "VoidResult",
    # Callback Type Aliases
    "AsyncCallback",
    "EventCallback",
    "Middleware",
    "SyncCallback",
    # Repository/UseCase Type Aliases
    "CRUDRepository",
    "ReadOnlyRepository",
    "ReadOnlyUseCase",
    "StandardUseCase",
    "WriteOnlyRepository",
    # Response Type Aliases
    "ApiResult",
    "ErrorResult",
    "PaginatedResult",
    # Other
    "CompositeSpec",
    "Spec",
    "Timestamp",
]
