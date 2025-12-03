"""Value objects for the Users bounded context.

Value objects are immutable and compared by their attributes, not identity.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 2.3**
"""

import re
from dataclasses import dataclass
from typing import Self

from core.base.domain.value_object import BaseValueObject


@dataclass(frozen=True, slots=True)
class Email(BaseValueObject):
    """Email value object with validation.

    Ensures email addresses are valid and normalized.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate email format."""
        if not self._is_valid_email(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
        # Normalize to lowercase
        object.__setattr__(self, "value", self.value.lower().strip())

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Check if email format is valid."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @classmethod
    def create(cls, value: str) -> Self:
        """Factory method to create Email."""
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PasswordHash(BaseValueObject):
    """Password hash value object.

    Stores hashed passwords with algorithm information.
    """

    value: str
    algorithm: str = "argon2id"

    def __post_init__(self) -> None:
        """Validate hash is not empty."""
        if not self.value:
            raise ValueError("Password hash cannot be empty")

    @classmethod
    def create(cls, hashed_value: str, algorithm: str = "argon2id") -> Self:
        """Factory method to create PasswordHash."""
        return cls(value=hashed_value, algorithm=algorithm)

    def __str__(self) -> str:
        return f"[HASHED:{self.algorithm}]"


@dataclass(frozen=True, slots=True)
class UserId(BaseValueObject):
    """User ID value object.

    Wraps user identifier for type safety.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate user ID is not empty."""
        if not self.value or not self.value.strip():
            raise ValueError("User ID cannot be empty")

    @classmethod
    def create(cls, value: str) -> Self:
        """Factory method to create UserId."""
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Username(BaseValueObject):
    """Username value object with validation.

    Ensures usernames follow naming rules.
    """

    value: str
    MIN_LENGTH: int = 3
    MAX_LENGTH: int = 50

    def __post_init__(self) -> None:
        """Validate username format."""
        if len(self.value) < self.MIN_LENGTH:
            raise ValueError(f"Username must be at least {self.MIN_LENGTH} characters")
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(f"Username must be at most {self.MAX_LENGTH} characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.value):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )

    @classmethod
    def create(cls, value: str) -> Self:
        """Factory method to create Username."""
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PhoneNumber(BaseValueObject):
    """Phone number value object with validation."""

    value: str
    country_code: str = ""

    def __post_init__(self) -> None:
        """Validate phone number format."""
        # Remove all non-digit characters for validation
        digits = re.sub(r"\D", "", self.value)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must have 10-15 digits")

    @classmethod
    def create(cls, value: str, country_code: str = "") -> Self:
        """Factory method to create PhoneNumber."""
        return cls(value=value, country_code=country_code)

    def __str__(self) -> str:
        if self.country_code:
            return f"+{self.country_code} {self.value}"
        return self.value
