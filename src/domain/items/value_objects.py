"""Value objects for Items bounded context.

**Feature: domain-consolidation-2025**
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from core.base.value_object import BaseValueObject


@dataclass(frozen=True, slots=True)
class ItemId(BaseValueObject):
    """Item identifier value object."""

    value: str

    def __post_init__(self) -> None:
        """Validate item ID."""
        if not self.value or not self.value.strip():
            raise ValueError("Item ID cannot be empty")

    @classmethod
    def create(cls, value: str) -> Self:
        """Factory method to create ItemId."""
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Price(BaseValueObject):
    """Price value object with tax calculation.

    Ensures prices are always positive.
    """

    amount: Decimal
    tax: Decimal | None = None

    def __post_init__(self) -> None:
        """Validate price."""
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.amount <= 0:
            raise ValueError("Price must be positive")
        if self.tax is not None:
            if not isinstance(self.tax, Decimal):
                object.__setattr__(self, "tax", Decimal(str(self.tax)))
            if self.tax < 0:
                raise ValueError("Tax cannot be negative")

    @property
    def total(self) -> Decimal:
        """Calculate total price with tax."""
        return self.amount + (self.tax or Decimal("0"))

    @classmethod
    def create(cls, amount: float, tax: float | None = None) -> Self:
        """Factory method to create Price."""
        return cls(
            amount=Decimal(str(amount)),
            tax=Decimal(str(tax)) if tax is not None else None,
        )

    def __str__(self) -> str:
        return f"{self.amount:.2f}"
