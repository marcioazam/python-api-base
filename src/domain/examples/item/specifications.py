"""Specifications for ItemExample.

Demonstrates:
- Specification[T] pattern with PEP 695 generics
- Composable specifications with &, |, ~ operators
- Business rule encapsulation

**Feature: example-system-demo**
"""

from decimal import Decimal

from core.base.patterns.specification import Specification
from domain.examples.item.entity import ItemExample, ItemExampleStatus


class ItemExampleActiveSpec(Specification[ItemExample]):
    """Specification for active items."""

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return candidate.status == ItemExampleStatus.ACTIVE and not candidate.is_deleted


class ItemExampleInStockSpec(Specification[ItemExample]):
    """Specification for items with available stock."""

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return candidate.quantity > 0


class ItemExamplePriceRangeSpec(Specification[ItemExample]):
    """Specification for items within a price range."""

    def __init__(self, min_price: Decimal, max_price: Decimal) -> None:
        self.min_price = min_price
        self.max_price = max_price

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return self.min_price <= candidate.price.amount <= self.max_price


class ItemExampleCategorySpec(Specification[ItemExample]):
    """Specification for items in a specific category."""

    def __init__(self, category: str) -> None:
        self.category = category

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return candidate.category == self.category


class ItemExampleAvailableSpec(Specification[ItemExample]):
    """Composite specification for available items.

    Item must be:
    - Active status
    - Not deleted
    - Has stock > 0
    """

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return candidate.is_available


class ItemExampleTagSpec(Specification[ItemExample]):
    """Specification for items with specific tag."""

    def __init__(self, tag: str) -> None:
        self.tag = tag

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return self.tag in candidate.tags


def available_items_in_category(category: str) -> Specification[ItemExample]:
    """Create composite spec for available items in category.

    Example:
        >>> electronics = available_items_in_category("Electronics")
        >>> items = [item for item in all_items if electronics.is_satisfied_by(item)]
    """
    return ItemExampleAvailableSpec() & ItemExampleCategorySpec(category)


def premium_items(min_price: Decimal = Decimal("100.00")) -> Specification[ItemExample]:
    """Create composite spec for premium items.

    Premium items are:
    - Active and not deleted
    - In stock (quantity > 0)
    - Price >= min_price (default $100)

    Example:
        >>> premium_spec = premium_items(Decimal("200.00"))
        >>> premium_electronics = premium_spec & ItemExampleCategorySpec("Electronics")
        >>> items = repository.find_all(premium_electronics)
    """
    return (
        ItemExampleActiveSpec()
        & ItemExampleInStockSpec()
        & ItemExamplePriceRangeSpec(min_price, Decimal("999999.99"))
    )


def clearance_items(max_price: Decimal = Decimal("20.00")) -> Specification[ItemExample]:
    """Create composite spec for clearance items.

    Clearance items are:
    - Active status
    - In stock
    - Low price (<= max_price, default $20)

    Example:
        >>> clearance = clearance_items(Decimal("15.00"))
        >>> sale_items = [item for item in inventory if clearance.is_satisfied_by(item)]
    """
    return (
        ItemExampleActiveSpec()
        & ItemExampleInStockSpec()
        & ItemExamplePriceRangeSpec(Decimal("0"), max_price)
    )


def popular_items_in_stock(tag: str = "popular") -> Specification[ItemExample]:
    """Create composite spec for popular items in stock.

    Example:
        >>> popular = popular_items_in_stock("bestseller")
        >>> featured_items = repository.find_all(popular)
    """
    return ItemExampleTagSpec(tag) & ItemExampleInStockSpec() & ItemExampleActiveSpec()


def premium_category_items(
    category: str, min_price: Decimal = Decimal("100.00")
) -> Specification[ItemExample]:
    """Create composite spec for premium items in a specific category.

    Combines category filtering with premium item criteria.

    Example:
        >>> premium_electronics = premium_category_items("Electronics", Decimal("500.00"))
        >>> for item in repository.find_all(premium_electronics):
        ...     print(f"{item.name}: ${item.price.amount}")
    """
    return premium_items(min_price) & ItemExampleCategorySpec(category)


def discountable_items(
    min_price: Decimal = Decimal("10.00"), max_price: Decimal = Decimal("200.00")
) -> Specification[ItemExample]:
    """Create composite spec for items eligible for discounts.

    Discountable items are:
    - Active and available
    - In stock
    - Within mid-range price (not too cheap, not premium)

    Example:
        >>> discountable = discountable_items(Decimal("20.00"), Decimal("150.00"))
        >>> discount_campaign_items = repository.find_all(discountable)
        >>> # Apply 15% discount to these items
    """
    return (
        ItemExampleAvailableSpec() & ItemExamplePriceRangeSpec(min_price, max_price)
    )


def featured_items(
    category: str, tag: str = "featured"
) -> Specification[ItemExample]:
    """Create composite spec for featured items in a category.

    Featured items are:
    - Available (active, not deleted, in stock)
    - In specific category
    - Tagged as featured

    Example:
        >>> featured_electronics = featured_items("Electronics", "featured")
        >>> homepage_items = repository.find_all(featured_electronics).take(10)
    """
    return (
        ItemExampleAvailableSpec()
        & ItemExampleCategorySpec(category)
        & ItemExampleTagSpec(tag)
    )


def out_of_stock_active_items() -> Specification[ItemExample]:
    """Create composite spec for active items that need restocking.

    Useful for inventory management reports.

    Example:
        >>> needs_restock = out_of_stock_active_items()
        >>> restock_list = repository.find_all(needs_restock)
        >>> for item in restock_list:
        ...     send_restock_alert(item.id, item.name)
    """
    return ItemExampleActiveSpec() & ~ItemExampleInStockSpec()
