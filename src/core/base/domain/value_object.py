"""Typed entity ID value objects with ULID validation.

Value Objects are immutable objects that are defined by their attributes rather
than identity. They are a fundamental building block in Domain-Driven Design.

Key Characteristics:
- Immutable (frozen=True)
- Compared by value, not identity
- No lifecycle (created, never modified)
- Interchangeable if values are equal

**Feature: domain-code-review-fixes**
**Validates: Requirements 4.2**

Examples:
    Basic Value Object:
        >>> from dataclasses import dataclass
        >>> @dataclass(frozen=True)
        ... class Email(BaseValueObject):
        ...     value: str
        ...
        ...     def __post_init__(self):
        ...         if "@" not in self.value:
        ...             raise ValueError("Invalid email format")
        ...
        >>> email1 = Email("user@example.com")
        >>> email2 = Email("user@example.com")
        >>> assert email1 == email2  # Value equality
        >>> assert email1 is not email2  # Different instances

    Money Value Object:
        >>> @dataclass(frozen=True)
        ... class Money(BaseValueObject):
        ...     amount: float
        ...     currency: str
        ...
        ...     def __post_init__(self):
        ...         if self.amount < 0:
        ...             raise ValueError("Amount cannot be negative")
        ...         if self.currency not in ["USD", "EUR", "BRL"]:
        ...             raise ValueError(f"Unsupported currency: {self.currency}")
        ...
        ...     def add(self, other: "Money") -> "Money":
        ...         if self.currency != other.currency:
        ...             raise ValueError("Cannot add different currencies")
        ...         return Money(self.amount + other.amount, self.currency)
        ...
        >>> price1 = Money(10.50, "USD")
        >>> price2 = Money(5.25, "USD")
        >>> total = price1.add(price2)
        >>> assert total.amount == 15.75

    Address Value Object:
        >>> @dataclass(frozen=True)
        ... class Address(BaseValueObject):
        ...     street: str
        ...     city: str
        ...     country: str
        ...     postal_code: str | None = None
        ...
        ...     def is_international(self, home_country: str) -> bool:
        ...         return self.country != home_country
        ...
        >>> addr = Address("123 Main St", "New York", "USA", "10001")
        >>> assert not addr.is_international("USA")
"""

from __future__ import annotations

import re
from abc import ABC
from dataclasses import dataclass
from typing import Self, Any

# ULID: 26 characters, Crockford Base32 alphabet (excludes I, L, O, U)
ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$", re.IGNORECASE)


@dataclass(frozen=True)
class BaseValueObject(ABC):
    """Base class for all value objects.

    Value objects are immutable and compared by their attributes.
    They have no identity and are interchangeable if their values are equal.

    Implements:
        - Value equality (__eq__ based on all attributes)
        - Hashing (__hash__ for use in sets/dicts)
        - Immutability (frozen=True enforced)

    Usage:
        Inherit from BaseValueObject and add your fields as dataclass attributes.
        Override __post_init__ for validation logic.

    Example:
        >>> @dataclass(frozen=True)
        ... class Temperature(BaseValueObject):
        ...     celsius: float
        ...
        ...     def __post_init__(self):
        ...         if self.celsius < -273.15:  # Absolute zero
        ...             raise ValueError("Temperature below absolute zero")
        ...
        ...     def to_fahrenheit(self) -> float:
        ...         return (self.celsius * 9/5) + 32
        ...
        >>> temp1 = Temperature(25.0)
        >>> temp2 = Temperature(25.0)
        >>> assert temp1 == temp2  # Value equality
        >>> assert temp1.to_fahrenheit() == 77.0
    """

    def __eq__(self, other: Any) -> bool:
        """Compare value objects by their attributes."""
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        """Hash based on all attributes."""
        return hash(tuple(sorted(self.__dict__.items())))


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
