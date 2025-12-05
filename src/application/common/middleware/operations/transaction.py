"""CQRS Middleware infrastructure.

This module provides:
- Middleware protocol for command processing
- TransactionMiddleware for automatic UoW management with configurable boundaries
- Transaction configuration per command
- Middleware chain composition support

**Feature: application-layer-improvements-2025**
**Validates: Requirements 2.3, Transaction boundary configuration**
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from core.base.patterns.result import Ok

logger = logging.getLogger(__name__)


# =============================================================================
# Transaction Configuration
# =============================================================================


@dataclass(frozen=True, slots=True)
class TransactionConfig:
    """Configuration for transaction boundaries.

    Allows commands to explicitly configure their transaction requirements.

    Attributes:
        enabled: Whether transaction is enabled (default: True).
        read_only: Mark transaction as read-only (optimization hint).
        isolation_level: Database isolation level (e.g., "READ_COMMITTED", "SERIALIZABLE").
        timeout_seconds: Transaction timeout in seconds.
        auto_commit: Auto-commit after successful execution (default: True).

    Example:
        >>> @dataclass(frozen=True, kw_only=True)
        ... class CreateUserCommand(BaseCommand):
        ...     email: str
        ...     password: str
        ...
        ...     @property
        ...     def transaction_config(self) -> TransactionConfig:
        ...         return TransactionConfig(
        ...             enabled=True,
        ...             read_only=False,
        ...             isolation_level="READ_COMMITTED",
        ...             timeout_seconds=30,
        ...         )

        >>> # Read-only query command (optimization)
        >>> @dataclass(frozen=True, kw_only=True)
        ... class ListUsersQuery(BaseQuery):
        ...     @property
        ...     def transaction_config(self) -> TransactionConfig:
        ...         return TransactionConfig(
        ...             enabled=True,
        ...             read_only=True,  # DB can optimize read-only transactions
        ...         )

        >>> # Command that doesn't need transaction (e.g., external API call)
        >>> @dataclass(frozen=True, kw_only=True)
        ... class SendEmailCommand(BaseCommand):
        ...     @property
        ...     def transaction_config(self) -> TransactionConfig:
        ...         return TransactionConfig(enabled=False)
    """

    enabled: bool = True
    read_only: bool = False
    isolation_level: str | None = None
    timeout_seconds: int | None = None
    auto_commit: bool = True


# Default configuration for commands without explicit config
DEFAULT_TRANSACTION_CONFIG = TransactionConfig(
    enabled=True,
    read_only=False,
    auto_commit=True,
)


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
    """Middleware that wraps command execution in a transaction with configurable boundaries.

    Auto-wraps commands in Unit of Work transaction for atomicity, with support for:
    - Per-command transaction configuration
    - Read-only transaction optimization
    - Isolation level control
    - Transaction timeouts
    - Opt-in/opt-out transaction support

    **Feature: application-layer-improvements-2025**
    **Validates: Requirements 109.3, Transaction boundary configuration**

    Example:
        >>> uow_factory = lambda: create_unit_of_work()
        >>> middleware = TransactionMiddleware(uow_factory)
        >>> bus.add_middleware(middleware)
        >>>
        >>> # Command with custom transaction config
        >>> @dataclass(frozen=True, kw_only=True)
        ... class CreateUserCommand(BaseCommand):
        ...     email: str
        ...
        ...     @property
        ...     def transaction_config(self) -> TransactionConfig:
        ...         return TransactionConfig(
        ...             enabled=True, isolation_level="READ_COMMITTED", timeout_seconds=30
        ...         )
    """

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        default_config: TransactionConfig | None = None,
    ) -> None:
        """Initialize transaction middleware.

        Args:
            uow_factory: Factory function that creates UoW instances.
            default_config: Default transaction config for commands without explicit config.
        """
        self._uow_factory = uow_factory
        self._default_config = default_config or DEFAULT_TRANSACTION_CONFIG

    def _get_transaction_config(self, command: Any) -> TransactionConfig:
        """Extract transaction config from command.

        Args:
            command: The command to extract config from.

        Returns:
            Transaction config (command's config or default).
        """
        # Try transaction_config property
        if hasattr(command, "transaction_config"):
            config = command.transaction_config
            if isinstance(config, TransactionConfig):
                return config
            # Handle callable property
            if callable(config):
                result = config()
                if isinstance(result, TransactionConfig):
                    return result

        # Try get_transaction_config method
        if hasattr(command, "get_transaction_config"):
            get_config = command.get_transaction_config
            if callable(get_config):
                result = get_config()
                if isinstance(result, TransactionConfig):
                    return result

        # Use default config
        return self._default_config

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[..., Any],
    ) -> Any:
        """Execute command within a transaction (if enabled).

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from the command handler.
        """
        config = self._get_transaction_config(command)
        command_name = type(command).__name__

        # If transaction is disabled, execute without transaction
        if not config.enabled:
            logger.debug(
                "transaction_disabled",
                extra={
                    "command_type": command_name,
                    "operation": "TRANSACTION_BYPASS",
                },
            )
            return await next_handler(command)

        # Execute within transaction
        uow = self._uow_factory()

        logger.debug(
            "transaction_started",
            extra={
                "command_type": command_name,
                "read_only": config.read_only,
                "isolation_level": config.isolation_level,
                "timeout_seconds": config.timeout_seconds,
                "operation": "TRANSACTION_START",
            },
        )

        async with uow:
            # Configure UoW if it supports configuration
            if config.read_only and hasattr(uow, "set_read_only"):
                uow.set_read_only(True)

            if config.isolation_level and hasattr(uow, "set_isolation_level"):
                uow.set_isolation_level(config.isolation_level)

            if config.timeout_seconds and hasattr(uow, "set_timeout"):
                uow.set_timeout(config.timeout_seconds)

            # Inject UoW into command if it has a uow attribute
            if hasattr(command, "uow"):
                command.uow = uow

            result = await next_handler(command)

            # Commit on success if auto_commit enabled
            if config.auto_commit and isinstance(result, Ok):
                await uow.commit()
                logger.debug(
                    "transaction_committed",
                    extra={
                        "command_type": command_name,
                        "operation": "TRANSACTION_COMMIT",
                    },
                )
            elif not config.auto_commit:
                logger.debug(
                    "transaction_auto_commit_disabled",
                    extra={
                        "command_type": command_name,
                        "operation": "TRANSACTION_NO_AUTO_COMMIT",
                    },
                )

            return result
