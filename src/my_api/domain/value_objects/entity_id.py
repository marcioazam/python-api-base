"""Typed entity ID value objects with ULID validation.

**Feature: domain-code-review-fixes**
**Validates: Requirements 4.2**
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

# ULID: 26 characters, Crockford Base32 alphabet (excludes I, L, O, U)
ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class EntityId:
    """Base immutable entity ID value object with ULID validation.

    ULIDs are 26-character strings using Crockford Base32 encoding.
    They are sortable, URL-safe, and case-insensitive.

    Attributes:
        value: The ULID string value.

    Example:
        ```python
        entity_id = EntityId("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        ```
    """

    value: str

    def __post_init__(self) -> None:
        """Validate ULID format."""
        if not self.value:
            raise ValueError("Entity ID cannot be empty")
        if not ULID_PATTERN.match(self.value):
            raise ValueError(
                f"Invalid ULID format: {self.value}. "
                "Must be 26 characters using Crockford Base32"
            )
        # Normalize to uppercase
        object.__setattr__(self, "value", self.value.upper())

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __hash__(self) -> int:
        """Return hash for use in sets/dicts."""
        return hash(self.value)

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Create EntityId from string."""
        return cls(value)


@dataclass(frozen=True, slots=True)
class ItemId(EntityId):
    """Typed ID for Item entities."""

    pass


@dataclass(frozen=True, slots=True)
class RoleId(EntityId):
    """Typed ID for Role entities."""

    pass


@dataclass(frozen=True, slots=True)
class UserId(EntityId):
    """Typed ID for User entities."""

    pass


@dataclass(frozen=True, slots=True)
class AuditLogId(EntityId):
    """Typed ID for AuditLog entities."""

    pass
