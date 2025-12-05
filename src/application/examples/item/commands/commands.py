"""CQRS Commands for ItemExample.

**Feature: application-common-integration**
**Validates: Requirements 2.1, 2.2, 2.3**
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from core.base.cqrs.command import BaseCommand


@dataclass(frozen=True, kw_only=True)
class CreateItemCommand(BaseCommand):
    """Command to create a new ItemExample."""

    name: str
    sku: str
    price_amount: Decimal
    price_currency: str = "BRL"
    description: str = ""
    quantity: int = 0
    category: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: str = "system"


@dataclass(frozen=True, kw_only=True)
class UpdateItemCommand(BaseCommand):
    """Command to update an existing ItemExample."""

    item_id: str
    name: str | None = None
    description: str | None = None
    price_amount: Decimal | None = None
    price_currency: str | None = None
    quantity: int | None = None
    category: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    updated_by: str = "system"


@dataclass(frozen=True, kw_only=True)
class DeleteItemCommand(BaseCommand):
    """Command to soft-delete an ItemExample."""

    item_id: str
    deleted_by: str = "system"
