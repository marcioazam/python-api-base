"""Item domain entity.

**Feature: domain-consolidation-2025**

Pure domain entity without persistence concerns.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self

from domain.items.value_objects import ItemId, Price


@dataclass
class ItemEntity:
    """Item domain entity.

    Pure domain entity - no ORM or persistence logic.
    """

    id: ItemId
    name: str
    price: Price
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate entity."""
        if not self.name or not self.name.strip():
            raise ValueError("Item name cannot be empty")
        if len(self.name) > 255:
            raise ValueError("Item name cannot exceed 255 characters")
        if self.description and len(self.description) > 1000:
            raise ValueError("Description cannot exceed 1000 characters")

    @classmethod
    def create(
        cls,
        item_id: str,
        name: str,
        price: float,
        tax: float | None = None,
        description: str | None = None,
    ) -> Self:
        """Factory method to create an Item.

        Args:
            item_id: Unique item identifier.
            name: Item name.
            price: Item price.
            tax: Optional tax amount.
            description: Optional item description.

        Returns:
            New ItemEntity instance.
        """
        return cls(
            id=ItemId.create(item_id),
            name=name.strip(),
            price=Price.create(price, tax),
            description=description.strip() if description else None,
        )

    def update_price(self, new_price: float, new_tax: float | None = None) -> None:
        """Update item price."""
        self.price = Price.create(new_price, new_tax)
        self.updated_at = datetime.now(UTC)

    def update_name(self, new_name: str) -> None:
        """Update item name."""
        if not new_name or not new_name.strip():
            raise ValueError("Item name cannot be empty")
        self.name = new_name.strip()
        self.updated_at = datetime.now(UTC)

    def update_description(self, new_description: str | None) -> None:
        """Update item description."""
        self.description = new_description.strip() if new_description else None
        self.updated_at = datetime.now(UTC)
