"""Shared DTOs for Example system.

**Feature: example-system-demo**
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class MoneyDTO(BaseModel):
    """Money value object DTO."""

    amount: Decimal = Field(..., ge=0, description="Amount value")
    currency: str = Field(default="BRL", min_length=3, max_length=3)

    model_config = {"frozen": True}
