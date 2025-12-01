"""Money value object with Decimal precision.

**Feature: domain-code-review-fixes**
**Validates: Requirements 4.1**
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Self


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
