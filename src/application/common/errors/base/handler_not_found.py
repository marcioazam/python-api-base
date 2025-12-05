"""Handler not found error.

Raised when no handler is registered for a command/query type.

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.errors.base.application_error import ApplicationError


class HandlerNotFoundError(ApplicationError):
    """Raised when no handler is registered for a command/query type.

    Attributes:
        handler_type: The handler type that was not found.

    Example:
        >>> raise HandlerNotFoundError(CreateUserCommand)
    """

    def __init__(self, handler_type: type) -> None:
        """Initialize handler not found error.

        Args:
            handler_type: The handler type that was not found.
        """
        self.handler_type = handler_type
        super().__init__(
            message=f"No handler registered for {handler_type.__name__}",
            code="HANDLER_NOT_FOUND",
            details={"handler_type": handler_type.__name__},
        )
