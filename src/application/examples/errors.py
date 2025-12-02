"""Error classes for Example system.

**Feature: example-system-demo**
"""


class UseCaseError(Exception):
    """Base error for use case failures."""

    def __init__(self, message: str, code: str = "USE_CASE_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(UseCaseError):
    """Entity not found error."""

    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} with id '{entity_id}' not found", "NOT_FOUND")
        self.entity = entity
        self.entity_id = entity_id


class ValidationError(UseCaseError):
    """Validation error."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
