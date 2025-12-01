"""Base handler classes for CQRS pattern.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.1, 3.2**
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from my_app.core.base.command import BaseCommand
from my_app.core.base.query import BaseQuery
from my_app.core.base.result import Result

TCommand = TypeVar("TCommand", bound=BaseCommand)
TQuery = TypeVar("TQuery", bound=BaseQuery)
TResult = TypeVar("TResult")


class CommandHandler(ABC, Generic[TCommand, TResult]):
    """Base class for command handlers.
    
    Command handlers process commands and return results.
    They should contain the application logic for executing commands.
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


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """Base class for query handlers.
    
    Query handlers process queries and return results.
    They should be read-only and not modify state.
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
