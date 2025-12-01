"""CQRS Middleware infrastructure.

This module provides:
- Middleware protocol for command processing
- TransactionMiddleware for automatic UoW management
- Middleware chain composition support

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 2.3**
"""

import logging
from typing import Any, Protocol, runtime_checkable
from collections.abc import Callable, Awaitable

from core.base.result import Ok

logger = logging.getLogger(__name__)


# =============================================================================
# Typed Middleware Protocol
# =============================================================================


@runtime_checkable
class Middleware[TCommand, TResult](Protocol):
    """Protocol for typed command middleware.

    Type Parameters:
        TCommand: The command type this middleware processes.
        TResult: The result type returned by the command.

    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 2.3**
    """

    async def __call__(
        self,
        command: TCommand,
        next_handler: Callable[[TCommand], Awaitable[TResult]],
    ) -> TResult:
        """Process command through middleware.

        Args:
            command: The command to process.
            next_handler: The next handler in the chain.

        Returns:
            Result from the command handler.
        """
        ...


# =============================================================================
# Transaction Middleware
# =============================================================================


class TransactionMiddleware:
    """Middleware that wraps command execution in a transaction.

    Auto-wraps commands in Unit of Work transaction for atomicity.

    **Feature: python-api-base-2025-review**
    **Validates: Requirements 109.3**

    Example:
        >>> uow_factory = lambda: create_unit_of_work()
        >>> middleware = TransactionMiddleware(uow_factory)
        >>> bus.add_middleware(middleware)
    """

    def __init__(self, uow_factory: Callable[[], Any]) -> None:
        """Initialize transaction middleware.

        Args:
            uow_factory: Factory function that creates UoW instances.
        """
        self._uow_factory = uow_factory

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[..., Any],
    ) -> Any:
        """Execute command within a transaction.

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from the command handler.
        """
        uow = self._uow_factory()
        async with uow:
            # Inject UoW into command if it has a uow attribute
            if hasattr(command, "uow"):
                command.uow = uow

            result = await next_handler(command)

            # Commit on success (Ok result)
            if isinstance(result, Ok):
                await uow.commit()
                logger.debug(f"Transaction committed for {type(command).__name__}")

            return result
