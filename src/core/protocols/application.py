"""Application layer protocol definitions.

Defines protocols for application patterns including event handlers,
CQRS commands/queries, and entity mappers.

Feature: file-size-compliance-phase2
"""

from abc import abstractmethod
from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class EventHandler[T](Protocol):
    """Protocol for domain event handlers.

    Defines the contract for handling domain events in an event-driven
    architecture.

    Type Parameters:
        T: The event type this handler processes.

    Feature: file-size-compliance-phase2
    """

    async def handle(self, event: T) -> None:
        """Handle a domain event.

        Args:
            event: The domain event to handle.
        """
        ...


class Command[ResultT](Protocol):
    """Protocol for CQRS commands.

    Commands represent intentions to change the system state.
    They should be immutable and contain all data needed for execution.

    Type Parameters:
        ResultT: The type of result returned after execution.

    Feature: file-size-compliance-phase2
    """

    @abstractmethod
    async def execute(self) -> ResultT:
        """Execute the command.

        Returns:
            The result of the command execution.
        """
        ...


class Query[ResultT](Protocol):
    """Protocol for CQRS queries.

    Queries represent requests for data without side effects.
    They should be immutable and contain all parameters needed for the query.

    Type Parameters:
        ResultT: The type of data returned by the query.

    Feature: file-size-compliance-phase2
    """

    @abstractmethod
    async def execute(self) -> ResultT:
        """Execute the query.

        Returns:
            The query result data.
        """
        ...


@runtime_checkable
class CommandHandler[T, ResultT](Protocol):
    """Protocol for command handlers.

    Command handlers process commands and return results.
    Implements the command side of CQRS pattern.

    Type Parameters:
        T: The command type this handler processes.
        ResultT: The type of result returned.

    Feature: file-size-compliance-phase2
    """

    async def handle(self, command: T) -> ResultT:
        """Handle a command.

        Args:
            command: The command to handle.

        Returns:
            The result of handling the command.
        """
        ...


@runtime_checkable
class QueryHandler[T, ResultT](Protocol):
    """Protocol for query handlers.

    Query handlers process queries and return data.
    Implements the query side of CQRS pattern.

    Type Parameters:
        T: The query type this handler processes.
        ResultT: The type of data returned.

    Feature: file-size-compliance-phase2
    """

    async def handle(self, query: T) -> ResultT:
        """Handle a query.

        Args:
            query: The query to handle.

        Returns:
            The query result data.
        """
        ...


@runtime_checkable
class Mapper[T, ResultT](Protocol):
    """Protocol for entity mappers.

    Mappers transform entities to DTOs and vice versa, providing
    bidirectional conversion between domain and application layers.

    Type Parameters:
        T: The source type (typically entity).
        ResultT: The target type (typically DTO).

    Feature: file-size-compliance-phase2
    """

    def to_dto(self, entity: T) -> ResultT:
        """Convert an entity to a DTO.

        Args:
            entity: The entity to convert.

        Returns:
            The converted DTO.
        """
        ...

    def to_entity(self, dto: ResultT) -> T:
        """Convert a DTO to an entity.

        Args:
            dto: The DTO to convert.

        Returns:
            The converted entity.
        """
        ...

    def to_dto_list(self, entities: Sequence[T]) -> Sequence[ResultT]:
        """Convert a sequence of entities to DTOs.

        Args:
            entities: Sequence of entities to convert.

        Returns:
            Sequence of converted DTOs.
        """
        ...

    def to_entity_list(self, dtos: Sequence[ResultT]) -> Sequence[T]:
        """Convert a sequence of DTOs to entities.

        Args:
            dtos: Sequence of DTOs to convert.

        Returns:
            Sequence of converted entities.
        """
        ...
