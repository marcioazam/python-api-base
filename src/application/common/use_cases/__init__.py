"""Use Cases for application layer.

Use Cases represent specific business operations that orchestrate
multiple services and enforce business rules.

**When to use UseCase vs Service:**

- **Service**: CRUD operations on a single entity (GenericService)
  - Example: ItemService.create(), ItemService.update()

- **UseCase**: Complex business operation that may involve multiple entities/services
  - Example: PlaceOrderUseCase.execute(), TransferMoneyUseCase.execute()

**Feature: architecture-consolidation-2025**
"""

from application.common.use_cases.base_use_case import (
    BaseUseCase,
    UseCaseError,
    UseCaseResult,
)

__all__ = [
    "BaseUseCase",
    "UseCaseError",
    "UseCaseResult",
]
