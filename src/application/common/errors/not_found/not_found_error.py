"""Entity not found error.

Raised when a requested entity cannot be found.

**Feature: python-api-base-2025-state-of-art**
"""

from typing import Any

from application.common.errors.base.application_error import ApplicationError


class NotFoundError(ApplicationError):
    """Entity not found error.

    Raised when a requested entity cannot be found in the system.

    Attributes:
        entity_type: Type of entity that was not found.
        entity_id: Identifier of the entity that was not found.

    Example:
        >>> raise NotFoundError(entity_type="User", entity_id="user-123")
    """

    def __init__(self, entity_type: str, entity_id: Any) -> None:
        """Initialize not found error.

        Args:
            entity_type: Type of entity.
            entity_id: Entity identifier.
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            code="NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
