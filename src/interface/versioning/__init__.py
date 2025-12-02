"""API versioning module.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 21.1-21.5**
"""

from .generic import (
    ApiVersion,
    BaseResponseTransformer,
    ResponseTransformer,
    VersionConfig,
    VersionedRouter,
    VersionFormat,
    VersionRouter,
    deprecated,
)

__all__ = [
    "ApiVersion",
    "BaseResponseTransformer",
    "ResponseTransformer",
    "VersionConfig",
    "VersionedRouter",
    "VersionFormat",
    "VersionRouter",
    "deprecated",
]
