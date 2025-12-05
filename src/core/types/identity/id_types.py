"""ID type definitions using PEP 593 Annotated types.

**Feature: core-types-split-2025**
**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 11.1**
"""

from typing import Annotated

from pydantic import Field, StringConstraints

__all__ = [
    "ULID",
    "UUID",
    "UUID7",
    "EntityId",
]

# PEP 695 type alias for entity identifiers
type EntityId = str | int
"""Generic entity identifier type (string or integer)."""

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

UUID7 = Annotated[
    str,
    StringConstraints(
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    ),
    Field(description="UUID v7 identifier (time-ordered, 36 characters)"),
]
"""UUID v7 string with validation (time-ordered, RFC 9562)."""
