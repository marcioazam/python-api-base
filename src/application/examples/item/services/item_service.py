"""ItemExample service using GenericService base.

Demonstrates how to use GenericService for CRUD operations with:
- Custom validation hooks
- Domain-specific business rules
- Integration with GenericCRUDRouter

**When to use Service vs UseCase:**

- **Service (this file)**: CRUD operations on a single entity
  - Multiple methods: create(), update(), delete(), get(), list()
  - Extends GenericService for common functionality

- **UseCase**: Complex business operation (see PlaceOrderUseCase)
  - Single method: execute()
  - Orchestrates multiple services/repositories

**Feature: python-api-base-2025-validation**
**Validates: Requirements 22.1, 22.2, 22.3, 22.4**
"""

from typing import Any

from application.common.services import (
    GenericService,
    IEventBus,
    IServiceMapper,
    ServiceError,
    ValidationError,
)
from application.examples.item.dtos import (
    ItemExampleCreate,
    ItemExampleResponse,
    ItemExampleUpdate,
)
from core.base.patterns.result import Err, Ok, Result
from core.base.repository.interface import IRepository
from domain.examples.item.entity import ItemExample


class ItemExampleService(
    GenericService[ItemExample, ItemExampleCreate, ItemExampleUpdate, ItemExampleResponse]
):
    """Service for ItemExample CRUD operations.

    Extends GenericService with custom validation:
    - SKU uniqueness validation on create
    - Price validation (must be positive)
    - Quantity validation (must be non-negative)

    Example:
        >>> service = ItemExampleService(repository, mapper)
        >>> result = await service.create(ItemExampleCreate(...))
        >>> # Or use router-compatible interface:
        >>> response = await service.get(item_id)

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 22.1, 22.2, 22.3, 22.4**
    """

    entity_name = "ItemExample"

    def __init__(
        self,
        repository: IRepository[ItemExample, ItemExampleCreate, ItemExampleUpdate, str],
        mapper: IServiceMapper[ItemExample, ItemExampleResponse] | None = None,
        event_bus: IEventBus | None = None,
        *,
        sku_validator: Any | None = None,
    ) -> None:
        """Initialize ItemExample service.

        Args:
            repository: ItemExample repository.
            mapper: Optional mapper for entity-to-DTO conversion.
            event_bus: Optional event bus for domain events.
            sku_validator: Optional SKU uniqueness validator.
        """
        super().__init__(repository, mapper, event_bus)
        self._sku_validator = sku_validator

    async def _pre_create(
        self, data: ItemExampleCreate
    ) -> Result[ItemExampleCreate, ServiceError]:
        """Validate before creating ItemExample.

        Validates:
        - SKU uniqueness (if validator provided)
        - Price is positive
        - Quantity is non-negative
        """
        # Validate price
        if data.price.amount <= 0:
            return Err(ValidationError("Price must be positive", "price"))

        # Validate quantity
        if data.quantity < 0:
            return Err(ValidationError("Quantity cannot be negative", "quantity"))

        # Validate SKU uniqueness
        if self._sku_validator is not None:
            existing = await self._sku_validator.get_by_sku(data.sku)
            if existing:
                return Err(
                    ValidationError(
                        f"SKU '{data.sku}' already exists",
                        "sku",
                        details={"existing_id": str(existing.id)},
                    )
                )

        return Ok(data)

    async def _pre_update(
        self,
        entity_id: Any,
        data: ItemExampleUpdate,
        existing: ItemExample,
    ) -> Result[ItemExampleUpdate, ServiceError]:
        """Validate before updating ItemExample.

        Validates:
        - Price is positive (if provided)
        - Quantity is non-negative (if provided)
        """
        # Validate price if provided
        if data.price is not None and data.price.amount <= 0:
            return Err(ValidationError("Price must be positive", "price"))

        # Validate quantity if provided
        if data.quantity is not None and data.quantity < 0:
            return Err(ValidationError("Quantity cannot be negative", "quantity"))

        return Ok(data)

    async def get_by_sku(self, sku: str) -> ItemExampleResponse | None:
        """Get ItemExample by SKU.

        Args:
            sku: Item SKU.

        Returns:
            ItemExample response or None if not found.
        """
        if self._sku_validator is None:
            raise ServiceError("SKU lookup not available")

        entity = await self._sku_validator.get_by_sku(sku)
        if entity is None:
            return None

        return self._to_response(entity)

    async def get_by_category(
        self,
        category: str,
        *,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ItemExampleResponse], int]:
        """Get ItemExamples by category.

        Args:
            category: Category to filter by.
            page: Page number.
            size: Items per page.

        Returns:
            Tuple of (items, total_count).
        """
        result = await self.get_all(
            skip=(page - 1) * size,
            limit=size,
            filters={"category": category},
        )
        if result.is_err():
            raise result.unwrap_err()

        items, total = result.unwrap()
        return list(items), total
