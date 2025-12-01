"""Common value objects with Decimal precision.

**Feature: domain-consolidation-2025**
**Validates: Requirements 4.1**

Provides reusable value objects for domain modeling:
- Money: Monetary values with currency support
- Percentage: Percentage values (0-100)
- Slug: URL-safe slugs
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Self


class CurrencyCode(str, Enum):
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


@dataclass(frozen=True, slots=True)
class Money:
    """Immutable money value object with currency.

    Uses Decimal for precise monetary calculations, avoiding
    floating-point precision issues.

    Attributes:
        amount: The monetary amount as Decimal.
        currency: ISO 4217 currency code (default: USD).

    Example:
        ```python
        price = Money(Decimal("29.99"), "USD")
        tax = Money(Decimal("2.40"), "USD")
        total = price + tax  # Money(Decimal("32.39"), "USD")
        ```
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate and normalize the amount."""
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        # Round to 2 decimal places
        rounded = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", rounded)

    def __add__(self, other: Money) -> Money:
        """Add two money values.

        Args:
            other: Money value to add.

        Returns:
            New Money with sum of amounts.

        Raises:
            ValueError: If currencies don't match.
        """
        self._validate_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        """Subtract two money values.

        Args:
            other: Money value to subtract.

        Returns:
            New Money with difference of amounts.

        Raises:
            ValueError: If currencies don't match.
        """
        self._validate_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: int | float | Decimal) -> Money:
        """Multiply money by a factor.

        Args:
            factor: Multiplication factor.

        Returns:
            New Money with multiplied amount.
        """
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __neg__(self) -> Money:
        """Negate the money amount."""
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        """Get absolute value."""
        return Money(abs(self.amount), self.currency)

    def __bool__(self) -> bool:
        """Check if amount is non-zero."""
        return self.amount != Decimal("0")

    def __lt__(self, other: Money) -> bool:
        """Less than comparison."""
        self._validate_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        """Less than or equal comparison."""
        self._validate_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        """Greater than comparison."""
        self._validate_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        """Greater than or equal comparison."""
        self._validate_same_currency(other)
        return self.amount >= other.amount

    def _validate_same_currency(self, other: Money) -> None:
        """Validate that currencies match."""
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot operate on different currencies: "
                f"{self.currency} vs {other.currency}"
            )

    @classmethod
    def zero(cls, currency: str = "USD") -> Self:
        """Create a zero money value."""
        return cls(Decimal("0"), currency)

    @classmethod
    def from_cents(cls, cents: int, currency: str = "USD") -> Self:
        """Create money from cents/minor units."""
        return cls(Decimal(cents) / Decimal("100"), currency)

    def to_cents(self) -> int:
        """Convert to cents/minor units."""
        return int(self.amount * Decimal("100"))

    def format(self, symbol: str | None = None) -> str:
        """Format as string with currency symbol.

        Args:
            symbol: Currency symbol (default: $ for USD).

        Returns:
            Formatted string like "$29.99".
        """
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "BRL": "R$"}
        sym = symbol or symbols.get(self.currency, self.currency + " ")
        return f"{sym}{self.amount:,.2f}"


@dataclass(frozen=True, slots=True)
class Percentage:
    """Percentage value object (0-100).

    Example:
        >>> discount = Percentage(15.5)  # 15.5%
        >>> factor = discount.as_factor()  # 0.155
    """

    value: float

    def __post_init__(self) -> None:
        """Validate percentage range."""
        if self.value < 0:
            raise ValueError("Percentage cannot be negative")
        if self.value > 100:
            raise ValueError("Percentage cannot exceed 100")

    def as_factor(self) -> float:
        """Convert to decimal factor (e.g., 15% -> 0.15)."""
        return self.value / 100

    def __str__(self) -> str:
        return f"{self.value}%"


@dataclass(frozen=True, slots=True)
class Slug:
    """URL-safe slug value object.

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
    def from_text(cls, text: str) -> Self:
        """Create slug from text."""
        slug = text.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        slug = re.sub(r"-+", "-", slug)
        return cls(slug)

    def __str__(self) -> str:
        return self.value
