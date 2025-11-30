"""Item use case with custom validation hooks.

**Feature: application-layer-code-review-v2, Tasks 3.1-3.2**
**Validates: Requirements 3.1, 3.2, 3.3**
"""

from typing import Final

from my_api.core.exceptions import ValidationError
from my_api.domain.entities.item import Item, ItemCreate, ItemResponse, ItemUpdate
from my_api.shared.mapper import IMapper
from my_api.shared.repository import IRepository
from my_api.shared.use_case import BaseUseCase


class ItemUseCase(BaseUseCase[Item, ItemCreate, ItemUpdate, ItemResponse]):
    """Use case for Item entity operations with custom validation.

    Implements business rule validation hooks for create and update operations.
    """

    # Business rule constants
    MIN_PRICE: Final[float] = 0.01
    MAX_PRICE: Final[float] = 1_000_000.00
    MAX_NAME_LENGTH: Final[int] = 255

    def __init__(
        self,
        repository: IRepository[Item, ItemCreate, ItemUpdate],
        mapper: IMapper[Item, ItemResponse],
    ) -> None:
        """Initialize Item use case with dependencies."""
        super().__init__(repository, mapper, entity_name="Item")

    @property
    def errors(self) -> list[dict[str, str]]:
        """Get validation errors list."""
        return getattr(self, "_errors", [])

    def _validate_create(self, data: ItemCreate) -> None:
        """Validate item creation data.

        Args:
            data: Item creation DTO.

        Raises:
            ValidationError: If business rules are violated.
        """
        errors: list[dict[str, str]] = []

        if data.price < self.MIN_PRICE:
            errors.append({
                "field": "price",
                "message": f"Price must be at least {self.MIN_PRICE}",
            })

        if data.price > self.MAX_PRICE:
            errors.append({
                "field": "price",
                "message": f"Price cannot exceed {self.MAX_PRICE}",
            })

        if data.name and len(data.name) > self.MAX_NAME_LENGTH:
            errors.append({
                "field": "name",
                "message": f"Name cannot exceed {self.MAX_NAME_LENGTH} characters",
            })

        if errors:
            raise ValidationError(
                message="Item validation failed",
                errors=errors,
            )

    def _validate_update(self, data: ItemUpdate) -> None:
        """Validate item update data.

        Args:
            data: Item update DTO.

        Raises:
            ValidationError: If business rules are violated.
        """
        errors: list[dict[str, str]] = []

        if data.price is not None:
            if data.price < self.MIN_PRICE:
                errors.append({
                    "field": "price",
                    "message": f"Price must be at least {self.MIN_PRICE}",
                })
            if data.price > self.MAX_PRICE:
                errors.append({
                    "field": "price",
                    "message": f"Price cannot exceed {self.MAX_PRICE}",
                })

        if data.name is not None and len(data.name) > self.MAX_NAME_LENGTH:
            errors.append({
                "field": "name",
                "message": f"Name cannot exceed {self.MAX_NAME_LENGTH} characters",
            })

        if errors:
            raise ValidationError(
                message="Item update validation failed",
                errors=errors,
            )
