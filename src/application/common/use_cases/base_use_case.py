"""Base UseCase for complex business operations.

A UseCase represents a single, specific business operation that:
- Has a single responsibility (one operation)
- May orchestrate multiple services/repositories
- Enforces business rules and invariants
- Returns a Result for explicit error handling

**When to use UseCase vs Service:**

- **Service (GenericService)**: CRUD operations on a single entity
  - Multiple methods: create(), update(), delete(), get(), list()
  - Example: ItemService, UserService

- **UseCase**: Complex business operation
  - Single method: execute()
  - May involve multiple entities/services
  - Example: PlaceOrderUseCase, TransferMoneyUseCase, RegisterUserUseCase

**Feature: architecture-consolidation-2025**
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from core.base.patterns.result import Err, Ok, Result
from core.shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Error Types
# =============================================================================


@dataclass(frozen=True)
class UseCaseError:
    """Error returned by use case operations.

    Attributes:
        message: Human-readable error message.
        code: Machine-readable error code.
        details: Additional error context.
    """

    message: str
    code: str = "USE_CASE_ERROR"
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# Common error factory functions
def validation_error(message: str, field: str | None = None) -> UseCaseError:
    """Create a validation error."""
    return UseCaseError(
        message=message,
        code="VALIDATION_ERROR",
        details={"field": field} if field else {},
    )


def not_found_error(entity_type: str, entity_id: Any) -> UseCaseError:
    """Create a not found error."""
    return UseCaseError(
        message=f"{entity_type} with id '{entity_id}' not found",
        code="NOT_FOUND",
        details={"entity_type": entity_type, "entity_id": str(entity_id)},
    )


def conflict_error(message: str) -> UseCaseError:
    """Create a conflict error."""
    return UseCaseError(message=message, code="CONFLICT")


def authorization_error(message: str = "Not authorized") -> UseCaseError:
    """Create an authorization error."""
    return UseCaseError(message=message, code="UNAUTHORIZED")


def business_rule_error(message: str, rule: str | None = None) -> UseCaseError:
    """Create a business rule violation error."""
    return UseCaseError(
        message=message,
        code="BUSINESS_RULE_VIOLATION",
        details={"rule": rule} if rule else {},
    )


# =============================================================================
# Type Aliases
# =============================================================================

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")

# Result type for use cases
type UseCaseResult[T] = Result[T, UseCaseError]


# =============================================================================
# Base UseCase
# =============================================================================


class BaseUseCase[TInput, TOutput](ABC):
    """Abstract base class for use cases.

    A UseCase encapsulates a single business operation with:
    - Input validation
    - Business rule enforcement
    - Orchestration of services/repositories
    - Result-based error handling

    Type Parameters:
        TInput: Input data type for the use case.
        TOutput: Output data type on success.

    Example:
        >>> @dataclass
        ... class PlaceOrderInput:
        ...     customer_id: str
        ...     items: list[OrderItem]
        ...     shipping_address: Address
        ...
        >>> @dataclass
        ... class PlaceOrderOutput:
        ...     order_id: str
        ...     total: Decimal
        ...     estimated_delivery: datetime
        ...
        >>> class PlaceOrderUseCase(BaseUseCase[PlaceOrderInput, PlaceOrderOutput]):
        ...     def __init__(self, order_service, inventory_service, payment_service):
        ...         super().__init__()
        ...         self._orders = order_service
        ...         self._inventory = inventory_service
        ...         self._payment = payment_service
        ...
        ...     async def execute(self, input: PlaceOrderInput) -> UseCaseResult[PlaceOrderOutput]:
        ...         # 1. Validate input
        ...         # 2. Check inventory
        ...         # 3. Process payment
        ...         # 4. Create order
        ...         # 5. Return result
        ...         ...

    **Feature: architecture-consolidation-2025**
    """

    def __init__(self) -> None:
        """Initialize use case with logger."""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._use_case_name = self.__class__.__name__

    @abstractmethod
    async def execute(self, input: TInput) -> UseCaseResult[TOutput]:
        """Execute the use case.

        This is the single entry point for the use case.
        Implementations should:
        1. Validate input
        2. Execute business logic
        3. Return Ok(output) on success or Err(error) on failure

        Args:
            input: Use case input data.

        Returns:
            Result containing output on success or UseCaseError on failure.
        """
        ...

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _ok(self, value: TOutput) -> UseCaseResult[TOutput]:
        """Create a successful result."""
        return Ok(value)

    def _err(self, error: UseCaseError) -> UseCaseResult[TOutput]:
        """Create an error result."""
        return Err(error)

    def _validation_error(
        self, message: str, field: str | None = None
    ) -> UseCaseResult[TOutput]:
        """Create a validation error result."""
        return Err(validation_error(message, field))

    def _not_found(
        self, entity_type: str, entity_id: Any
    ) -> UseCaseResult[TOutput]:
        """Create a not found error result."""
        return Err(not_found_error(entity_type, entity_id))

    def _conflict(self, message: str) -> UseCaseResult[TOutput]:
        """Create a conflict error result."""
        return Err(conflict_error(message))

    def _unauthorized(self, message: str = "Not authorized") -> UseCaseResult[TOutput]:
        """Create an authorization error result."""
        return Err(authorization_error(message))

    def _business_error(
        self, message: str, rule: str | None = None
    ) -> UseCaseResult[TOutput]:
        """Create a business rule error result."""
        return Err(business_rule_error(message, rule))

    def _log_start(self, input: TInput) -> None:
        """Log use case start."""
        self._logger.info("Starting %s", self._use_case_name)

    def _log_success(self, output: TOutput) -> None:
        """Log use case success."""
        self._logger.info("Completed %s successfully", self._use_case_name)

    def _log_error(self, error: UseCaseError) -> None:
        """Log use case error."""
        self._logger.warning(
            "Failed %s: [%s] %s",
            self._use_case_name,
            error.code,
            error.message,
        )
