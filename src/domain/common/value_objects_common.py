"""Common value objects for domain modeling.

Provides reusable value objects with validation.
Uses PEP 695 type parameter syntax.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from src.core.base.value_object import BaseValueObject as ValueObject


class CurrencyCode(Enum):
    """ISO 4217 currency codes."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    CNY = "CNY"
    BRL = "BRL"
    INR = "INR"


@dataclass(frozen=True)
class Money[TCurrency: CurrencyCode](ValueObject):
    """Money value object with currency.

    Type Parameters:
        TCurrency: Currency type (must be CurrencyCode).

    Example:
        >>> price = Money(Decimal("19.99"), CurrencyCode.USD)
        >>> tax = Money(Decimal("2.00"), CurrencyCode.USD)
        >>> total = price + tax
    """

    amount: Decimal
    currency: TCurrency

    def __post_init__(self) -> None:
        """Validate money value."""
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")

        if not isinstance(self.currency, CurrencyCode):
            raise ValueError(f"Invalid currency: {self.currency}")

    def __add__(self, other: "Money[TCurrency]") -> "Money[TCurrency]":
        """Add two money amounts."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money[TCurrency]") -> "Money[TCurrency]":
        """Subtract two money amounts."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValueError("Result cannot be negative")
        return Money(result_amount, self.currency)

    def __mul__(self, factor: int | float | Decimal) -> "Money[TCurrency]":
        """Multiply money by a factor."""
        if not isinstance(factor, Decimal):
            factor = Decimal(str(factor))
        return Money(self.amount * factor, self.currency)

    def __truediv__(self, divisor: int | float | Decimal) -> "Money[TCurrency]":
        """Divide money by a divisor."""
        if not isinstance(divisor, Decimal):
            divisor = Decimal(str(divisor))
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Money(self.amount / divisor, self.currency)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.amount} {self.currency.value}"

    def to_cents(self) -> int:
        """Convert to cents (smallest currency unit)."""
        return int(self.amount * 100)

    @classmethod
    def from_cents(cls, cents: int, currency: CurrencyCode) -> "Money[CurrencyCode]":
        """Create from cents."""
        return cls(Decimal(cents) / 100, currency)

    @classmethod
    def zero(cls, currency: CurrencyCode) -> "Money[CurrencyCode]":
        """Create zero money."""
        return cls(Decimal("0"), currency)


@dataclass(frozen=True)
class Email(ValueObject):
    """Email address value object.

    Example:
        >>> email = Email("user@example.com")
        >>> print(email.domain)  # "example.com"
    """

    value: str

    def __post_init__(self) -> None:
        """Validate email format."""
        if not self.value:
            raise ValueError("Email cannot be empty")

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, self.value):
            raise ValueError(f"Invalid email format: {self.value}")

        if len(self.value) > 254:
            raise ValueError("Email too long")

    @property
    def local_part(self) -> str:
        """Get the local part (before @)."""
        return self.value.split("@")[0]

    @property
    def domain(self) -> str:
        """Get the domain part (after @)."""
        return self.value.split("@")[1]

    def __str__(self) -> str:
        """String representation."""
        return self.value


@dataclass(frozen=True)
class PhoneNumber(ValueObject):
    """Phone number value object.

    Example:
        >>> phone = PhoneNumber("+1-555-123-4567")
        >>> print(phone.digits_only)  # "15551234567"
    """

    value: str

    def __post_init__(self) -> None:
        """Validate phone number."""
        if not self.value:
            raise ValueError("Phone number cannot be empty")

        digits = re.sub(r"\D", "", self.value)

        if len(digits) < 7:
            raise ValueError("Phone number too short")

        if len(digits) > 15:
            raise ValueError("Phone number too long")

    @property
    def digits_only(self) -> str:
        """Get only the digits."""
        return re.sub(r"\D", "", self.value)

    def __str__(self) -> str:
        """String representation."""
        return self.value


@dataclass(frozen=True)
class Url(ValueObject):
    """URL value object.

    Example:
        >>> url = Url("https://example.com/path")
        >>> print(url.scheme)  # "https"
    """

    value: str

    def __post_init__(self) -> None:
        """Validate URL format."""
        if not self.value:
            raise ValueError("URL cannot be empty")

        pattern = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"
        if not re.match(pattern, self.value):
            raise ValueError(f"Invalid URL format: {self.value}")

    @property
    def scheme(self) -> str:
        """Get the URL scheme."""
        return self.value.split("://")[0]

    @property
    def host(self) -> str:
        """Get the host part."""
        without_scheme = self.value.split("://")[1]
        return without_scheme.split("/")[0]

    def __str__(self) -> str:
        """String representation."""
        return self.value


@dataclass(frozen=True)
class Percentage(ValueObject):
    """Percentage value object.

    Example:
        >>> discount = Percentage(15.5)  # 15.5%
        >>> factor = discount.as_factor()  # 0.155
    """

    value: float

    def __post_init__(self) -> None:
        """Validate percentage."""
        if self.value < 0:
            raise ValueError("Percentage cannot be negative")

        if self.value > 100:
            raise ValueError("Percentage cannot exceed 100")

    def as_factor(self) -> float:
        """Convert to decimal factor (e.g., 15% -> 0.15)."""
        return self.value / 100

    def __str__(self) -> str:
        """String representation."""
        return f"{self.value}%"


@dataclass(frozen=True)
class Slug(ValueObject):
    """URL slug value object.

    Example:
        >>> slug = Slug.from_text("Hello World!")
        >>> print(slug.value)  # "hello-world"
    """

    value: str

    def __post_init__(self) -> None:
        """Validate slug format."""
        if not self.value:
            raise ValueError("Slug cannot be empty")

        pattern = r"^[a-z0-9-]+$"
        if not re.match(pattern, self.value):
            raise ValueError(f"Invalid slug format: {self.value}")

        if self.value.startswith("-") or self.value.endswith("-"):
            raise ValueError("Slug cannot start or end with hyphen")

        if "--" in self.value:
            raise ValueError("Slug cannot contain consecutive hyphens")

    @classmethod
    def from_text(cls, text: str) -> "Slug":
        """Create slug from text."""
        slug = text.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        slug = re.sub(r"-+", "-", slug)
        return cls(slug)

    def __str__(self) -> str:
        """String representation."""
        return self.value
