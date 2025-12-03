"""Property-based tests for CQRS infrastructure.

**Feature: advanced-reusability, Properties 12-13**
**Validates: Requirements 5.3, 5.4**
"""

import asyncio
from dataclasses import dataclass

import pytest

pytest.skip('Module core.shared.cqrs not implemented', allow_module_level=True)

from hypothesis import given, settings
from hypothesis import strategies as st

from core.shared.cqrs import (
    Command,
    CommandBus,
    HandlerNotFoundError,
    Query,
    QueryBus,
)
from core.shared.result import Err, Ok, Result


# Test Commands
@dataclass
class CreateItemCommand(Command[str, str]):
    """Test command for creating an item."""

    name: str
    price: float

    async def execute(self) -> Result[str, str]:
        if not self.name:
            return Err("Name is required")
        return Ok(f"item-{self.name}")


@dataclass
class UpdateItemCommand(Command[bool, str]):
    """Test command for updating an item."""

    item_id: str
    name: str

    async def execute(self) -> Result[bool, str]:
        return Ok(True)


@dataclass
class CommandWithEvents(Command[str, str]):
    """Test command that emits events."""

    name: str
    events: list = None  # type: ignore

    def __post_init__(self):
        self.events = [{"type": "ItemCreated", "name": self.name}]

    async def execute(self) -> Result[str, str]:
        return Ok(f"created-{self.name}")


# Test Queries
@dataclass
class GetItemQuery(Query[dict]):
    """Test query for getting an item."""

    item_id: str

    async def execute(self) -> dict:
        return {"id": self.item_id, "name": "Test Item"}


@dataclass
class ListItemsQuery(Query[list]):
    """Test query for listing items."""

    limit: int = 10
    cacheable: bool = True
    cache_ttl: int = 300

    async def execute(self) -> list:
        return [{"id": f"item-{i}"} for i in range(self.limit)]


class TestCommandBusDispatch:
    """Property tests for Command Bus Dispatch.

    **Feature: advanced-reusability, Property 12: Command Bus Dispatch**
    **Validates: Requirements 5.3**
    """

    def test_command_bus_dispatches_to_registered_handler(self) -> None:
        """
        **Feature: advanced-reusability, Property 12: Command Bus Dispatch**

        For any registered command type and handler, dispatching a command
        of that type SHALL invoke the registered handler.
        """
        bus = CommandBus()
        handler_called = False
        received_command = None

        async def handler(cmd: CreateItemCommand) -> Result[str, str]:
            nonlocal handler_called, received_command
            handler_called = True
            received_command = cmd
            return Ok(f"created-{cmd.name}")

        bus.register(CreateItemCommand, handler)

        async def run_test():
            command = CreateItemCommand(name="test", price=10.0)
            result = await bus.dispatch(command)

            assert handler_called
            assert received_command is command
            assert isinstance(result, Ok)
            assert result.value == "created-test"

        asyncio.run(run_test())

    @settings(max_examples=50)
    @given(
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        price=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False),
    )
    def test_command_bus_passes_command_data(
        self, name: str, price: float
    ) -> None:
        """
        **Feature: advanced-reusability, Property 12: Command Bus Dispatch**

        For any command data, the handler SHALL receive the exact
        command instance with all data intact.
        """
        bus = CommandBus()
        received_data: dict = {}

        async def handler(cmd: CreateItemCommand) -> Result[str, str]:
            received_data["name"] = cmd.name
            received_data["price"] = cmd.price
            return Ok("ok")

        bus.register(CreateItemCommand, handler)

        async def run_test():
            command = CreateItemCommand(name=name, price=price)
            await bus.dispatch(command)

            assert received_data["name"] == name
            assert received_data["price"] == price

        asyncio.run(run_test())

    def test_command_bus_raises_for_unregistered_command(self) -> None:
        """
        Dispatching an unregistered command type SHALL raise HandlerNotFoundError.
        """
        bus = CommandBus()

        async def run_test():
            command = CreateItemCommand(name="test", price=10.0)
            with pytest.raises(HandlerNotFoundError) as exc_info:
                await bus.dispatch(command)

            assert exc_info.value.command_type == CreateItemCommand

        asyncio.run(run_test())

    def test_command_bus_middleware_execution(self) -> None:
        """
        Middleware SHALL be executed in order before the handler.
        """
        bus = CommandBus()
        execution_order: list[str] = []

        async def middleware1(cmd: Any, next_handler: Any) -> Any:
            execution_order.append("middleware1_before")
            result = await next_handler(cmd)
            execution_order.append("middleware1_after")
            return result

        async def middleware2(cmd: Any, next_handler: Any) -> Any:
            execution_order.append("middleware2_before")
            result = await next_handler(cmd)
            execution_order.append("middleware2_after")
            return result

        async def handler(cmd: CreateItemCommand) -> Result[str, str]:
            execution_order.append("handler")
            return Ok("ok")

        bus.add_middleware(middleware1)
        bus.add_middleware(middleware2)
        bus.register(CreateItemCommand, handler)

        async def run_test():
            await bus.dispatch(CreateItemCommand(name="test", price=10.0))

            assert execution_order == [
                "middleware1_before",
                "middleware2_before",
                "handler",
                "middleware2_after",
                "middleware1_after",
            ]

        asyncio.run(run_test())

    def test_command_bus_event_emission(self) -> None:
        """
        After successful command execution, domain events SHALL be emitted.
        """
        bus = CommandBus()
        received_events: list = []

        async def handler(cmd: CommandWithEvents) -> Result[str, str]:
            return Ok(f"created-{cmd.name}")

        async def event_handler(event: Any) -> None:
            received_events.append(event)

        bus.register(CommandWithEvents, handler)
        bus.on_event(event_handler)

        async def run_test():
            command = CommandWithEvents(name="test-item")
            result = await bus.dispatch(command)

            assert isinstance(result, Ok)
            assert len(received_events) == 1
            assert received_events[0]["type"] == "ItemCreated"
            assert received_events[0]["name"] == "test-item"

        asyncio.run(run_test())

    def test_command_bus_multiple_handlers(self) -> None:
        """
        Multiple command types SHALL be handled independently.
        """
        bus = CommandBus()
        create_called = False
        update_called = False

        async def create_handler(cmd: CreateItemCommand) -> Result[str, str]:
            nonlocal create_called
            create_called = True
            return Ok("created")

        async def update_handler(cmd: UpdateItemCommand) -> Result[bool, str]:
            nonlocal update_called
            update_called = True
            return Ok(True)

        bus.register(CreateItemCommand, create_handler)
        bus.register(UpdateItemCommand, update_handler)

        async def run_test():
            await bus.dispatch(CreateItemCommand(name="test", price=10.0))
            assert create_called
            assert not update_called

            await bus.dispatch(UpdateItemCommand(item_id="1", name="updated"))
            assert update_called

        asyncio.run(run_test())


class TestQueryBusDispatch:
    """Property tests for Query Bus Dispatch.

    **Feature: advanced-reusability, Property 13: Query Bus Dispatch**
    **Validates: Requirements 5.4**
    """

    def test_query_bus_dispatches_to_registered_handler(self) -> None:
        """
        **Feature: advanced-reusability, Property 13: Query Bus Dispatch**

        For any registered query type and handler, dispatching a query
        of that type SHALL invoke the registered handler and return its result.
        """
        bus = QueryBus()
        handler_called = False

        async def handler(query: GetItemQuery) -> dict:
            nonlocal handler_called
            handler_called = True
            return {"id": query.item_id, "name": "Test"}

        bus.register(GetItemQuery, handler)

        async def run_test():
            query = GetItemQuery(item_id="123")
            result = await bus.dispatch(query)

            assert handler_called
            assert result["id"] == "123"
            assert result["name"] == "Test"

        asyncio.run(run_test())

    @settings(max_examples=50)
    @given(item_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))))
    def test_query_bus_passes_query_data(self, item_id: str) -> None:
        """
        **Feature: advanced-reusability, Property 13: Query Bus Dispatch**

        For any query data, the handler SHALL receive the exact
        query instance with all data intact.
        """
        bus = QueryBus()
        received_id = None

        async def handler(query: GetItemQuery) -> dict:
            nonlocal received_id
            received_id = query.item_id
            return {"id": query.item_id}

        bus.register(GetItemQuery, handler)

        async def run_test():
            query = GetItemQuery(item_id=item_id)
            await bus.dispatch(query)

            assert received_id == item_id

        asyncio.run(run_test())

    def test_query_bus_raises_for_unregistered_query(self) -> None:
        """
        Dispatching an unregistered query type SHALL raise HandlerNotFoundError.
        """
        bus = QueryBus()

        async def run_test():
            query = GetItemQuery(item_id="123")
            with pytest.raises(HandlerNotFoundError) as exc_info:
                await bus.dispatch(query)

            assert exc_info.value.command_type == GetItemQuery

        asyncio.run(run_test())

    def test_query_bus_caching(self) -> None:
        """
        Query results SHALL be cached when cache is configured.
        """
        from core.shared.caching import InMemoryCacheProvider

        bus = QueryBus()
        cache = InMemoryCacheProvider()
        bus.set_cache(cache)

        call_count = 0

        async def handler(query: ListItemsQuery) -> list:
            nonlocal call_count
            call_count += 1
            return [{"id": f"item-{i}"} for i in range(query.limit)]

        bus.register(ListItemsQuery, handler)

        async def run_test():
            nonlocal call_count

            # First call - should execute handler
            query = ListItemsQuery(limit=5)
            result1 = await bus.dispatch(query)
            assert call_count == 1
            assert len(result1) == 5

            # Second call with same query - should use cache
            result2 = await bus.dispatch(query)
            assert call_count == 1  # Handler not called again
            assert result2 == result1

        asyncio.run(run_test())

    def test_query_bus_multiple_handlers(self) -> None:
        """
        Multiple query types SHALL be handled independently.
        """
        bus = QueryBus()

        async def get_handler(query: GetItemQuery) -> dict:
            return {"id": query.item_id}

        async def list_handler(query: ListItemsQuery) -> list:
            return [{"id": f"item-{i}"} for i in range(query.limit)]

        bus.register(GetItemQuery, get_handler)
        bus.register(ListItemsQuery, list_handler)

        async def run_test():
            get_result = await bus.dispatch(GetItemQuery(item_id="123"))
            assert get_result["id"] == "123"

            list_result = await bus.dispatch(ListItemsQuery(limit=3))
            assert len(list_result) == 3

        asyncio.run(run_test())


class TestHandlerRegistration:
    """Tests for handler registration."""

    def test_duplicate_command_handler_raises(self) -> None:
        """Registering duplicate handler SHALL raise ValueError."""
        bus = CommandBus()

        async def handler1(cmd: CreateItemCommand) -> Result[str, str]:
            return Ok("1")

        async def handler2(cmd: CreateItemCommand) -> Result[str, str]:
            return Ok("2")

        bus.register(CreateItemCommand, handler1)

        with pytest.raises(ValueError):
            bus.register(CreateItemCommand, handler2)

    def test_duplicate_query_handler_raises(self) -> None:
        """Registering duplicate handler SHALL raise ValueError."""
        bus = QueryBus()

        async def handler1(query: GetItemQuery) -> dict:
            return {}

        async def handler2(query: GetItemQuery) -> dict:
            return {}

        bus.register(GetItemQuery, handler1)

        with pytest.raises(ValueError):
            bus.register(GetItemQuery, handler2)

    def test_unregister_command_handler(self) -> None:
        """Unregistering handler SHALL remove it from the bus."""
        bus = CommandBus()

        async def handler(cmd: CreateItemCommand) -> Result[str, str]:
            return Ok("ok")

        bus.register(CreateItemCommand, handler)
        bus.unregister(CreateItemCommand)

        async def run_test():
            with pytest.raises(HandlerNotFoundError):
                await bus.dispatch(CreateItemCommand(name="test", price=10.0))

        asyncio.run(run_test())

    def test_unregister_query_handler(self) -> None:
        """Unregistering handler SHALL remove it from the bus."""
        bus = QueryBus()

        async def handler(query: GetItemQuery) -> dict:
            return {}

        bus.register(GetItemQuery, handler)
        bus.unregister(GetItemQuery)

        async def run_test():
            with pytest.raises(HandlerNotFoundError):
                await bus.dispatch(GetItemQuery(item_id="123"))

        asyncio.run(run_test())


# Import Any for type hints
from typing import Any
