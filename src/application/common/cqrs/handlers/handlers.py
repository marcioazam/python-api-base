"""Base handler classes for CQRS pattern.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.1, 3.2**
**Updated: state-of-art-generics-review - Task 1.2**
"""

from abc import ABC, abstractmethod

from core.base.cqrs.command import BaseCommand
from core.base.cqrs.query import BaseQuery
from core.base.patterns.result import Result


class CommandHandler[TCommand: BaseCommand, TResult](ABC):
    """Base class for command handlers.

    Command handlers process commands and return results.
    They should contain the application logic for executing commands.

    Type Parameters:
        TCommand: The command type this handler processes (must extend BaseCommand).
        TResult: The success result type returned by the handler.
    """

    @abstractmethod
    async def handle(self, command: TCommand) -> Result[TResult, Exception]:
        """Handle a command.

        Args:
            command: Command to handle.

        Returns:
            Result containing success value or error.
        """
        ...


class QueryHandler[TQuery: BaseQuery, TResult](ABC):
    """Base class for query handlers.

    Query handlers process queries and return results.
    They should be read-only and not modify state.

    Type Parameters:
        TQuery: The query type this handler processes (must extend BaseQuery).
        TResult: The result type returned by the handler.
    """

    @abstractmethod
    async def handle(self, query: TQuery) -> Result[TResult, Exception]:
        """Handle a query.

        Args:
            query: Query to handle.

        Returns:
            Result containing success value or error.
        """
        ...
