"""Core type definitions using PEP 593 Annotated types and PEP 695 type aliases.

Organized into subpackages by category:
- identity/: ID types (ULID, UUID, UUID7, EntityId)
- data/: JSON, numeric, and string types
- patterns/: Result pattern and callback types
- domain/: Repository and security types
- aliases: PEP 695 type aliases (AsyncResult, Handler, Validator, Filter)

**Feature: core-types-split-2025**
**Feature: python-api-base-2025-validation**

Provides reusable type aliases with built-in validation constraints.
Refactored from monolithic types.py into focused modules.
"""

# ID Types
from core.types.identity import ULID, UUID, UUID7

# JSON Type Aliases
from core.types.data import (
    FilterDict,
    Headers,
    JSONArray,
    JSONObject,
    JSONPrimitive,
    JSONValue,
    QueryParams,
    SortOrder,
    # Numeric Types
    NonNegativeFloat,
    NonNegativeInt,
    PageNumber,
    PageSize,
    Percentage,
    PercentageRange,
    PositiveFloat,
    PositiveInt,
    # String Types
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
    URLPath,
    VersionStr,
)

# Repository/UseCase Type Aliases
from core.types.domain import (
    ApiResult,
    CRUDRepository,
    ErrorResult,
    PaginatedResult,
    ReadOnlyRepository,
    ReadOnlyUseCase,
    StandardUseCase,
    WriteOnlyRepository,
    # Security Types
    JWTToken,
    Password,
    SecurePassword,
)

# Result Pattern and Callback Type Aliases
from core.types.patterns import (
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

# PEP 695 Type Aliases (Python 3.12+)
from core.types.aliases import (
    AsyncFilter,
    AsyncHandler,
    AsyncMapper,
    AsyncResult,
    AsyncValidator,
    Callback,
    Factory,
    Filter,
    Handler,
    Mapper,
    Predicate,
    SyncHandler,
    Validator,
    ValidatorWithError,
    AsyncCallback as AsyncCallbackAlias,
    AsyncFactory,
)

__all__ = [
    # ID Types
    "ULID",
    "UUID",
    "UUID7",
    # Response Type Aliases
    "ApiResult",
    # Callback Type Aliases
    "AsyncCallback",
    "AsyncCallbackAlias",
    # Repository/UseCase Type Aliases
    "CRUDRepository",
    # Other
    "CompositeSpec",
    # String Types
    "Email",
    "EntityId",
    "ErrorResult",
    "EventCallback",
    # Result Pattern Type Aliases
    "Failure",
    # Filter/Query Type Aliases
    "FilterDict",
    "Headers",
    "HttpUrl",
    "ISODateStr",
    # JSON Type Aliases
    "JSONArray",
    "JSONObject",
    "JSONPrimitive",
    "JSONValue",
    # Security Types
    "JWTToken",
    "LongStr",
    "MediumStr",
    "Middleware",
    "NonEmptyStr",
    # Numeric Types
    "NonNegativeFloat",
    "NonNegativeInt",
    "OperationResult",
    # Pagination Types
    "PageNumber",
    "PageSize",
    "PaginatedResult",
    "Password",
    "Percentage",
    "PercentageRange",
    "PhoneNumber",
    "PositiveFloat",
    "PositiveInt",
    "QueryParams",
    "ReadOnlyRepository",
    "ReadOnlyUseCase",
    "SecurePassword",
    "ShortStr",
    "Slug",
    "SortOrder",
    "Spec",
    "StandardUseCase",
    "Success",
    "SyncCallback",
    "Timestamp",
    "TrimmedStr",
    "URLPath",
    "VersionStr",
    "VoidResult",
    "WriteOnlyRepository",
    # PEP 695 Type Aliases (Python 3.12+)
    "AsyncFilter",
    "AsyncHandler",
    "AsyncMapper",
    "AsyncResult",
    "AsyncValidator",
    "Callback",
    "Factory",
    "AsyncFactory",
    "Filter",
    "Handler",
    "Mapper",
    "Predicate",
    "SyncHandler",
    "Validator",
    "ValidatorWithError",
]
