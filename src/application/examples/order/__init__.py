"""Order example module.

Demonstrates the UseCase pattern for complex business operations.

**Feature: architecture-consolidation-2025**
"""

from application.examples.order.use_cases import PlaceOrderUseCase
from application.examples.order.dtos import (
    PlaceOrderInput,
    PlaceOrderOutput,
    OrderItemInput,
)

__all__ = [
    "PlaceOrderUseCase",
    "PlaceOrderInput",
    "PlaceOrderOutput",
    "OrderItemInput",
]
