"""DTOs for ItemExample.

Demonstrates:
- Pydantic v2 models with validation
- Create/Update/Response pattern
- Computed fields
- Field validators

**Feature: example-system-demo**
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator

from application.examples.shared.dtos import MoneyDTO
from domain.examples.item.entity import ItemExampleStatus


class ItemExampleCreate(BaseModel):
    """DTO for creating an ItemExample."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    sku: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z0-9\-]+$")
    price: MoneyDTO
    quantity: int = Field(default=0, ge=0)
    category: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sku")
    @classmethod
    def uppercase_sku(cls, v: str) -> str:
        return v.upper()

    @field_validator("tags")
    @classmethod
    def lowercase_tags(cls, v: list[str]) -> list[str]:
        return [tag.lower().strip() for tag in v if tag.strip()]


class ItemExampleUpdate(BaseModel):
    """DTO for updating an ItemExample."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: MoneyDTO | None = None
    quantity: int | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None
    status: ItemExampleStatus | None = None


class ItemExampleResponse(BaseModel):
    """Response DTO for ItemExample."""

    id: str
    name: str
    description: str
    sku: str
    price: MoneyDTO
    quantity: int
    status: str
    category: str
    tags: list[str]
    is_available: bool
    total_value: MoneyDTO
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    model_config = {"from_attributes": True}


class ItemExampleListResponse(BaseModel):
    """List response with summary."""

    items: list[ItemExampleResponse]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 1
        return (self.total + self.page_size - 1) // self.page_size

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
