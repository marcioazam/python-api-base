"""Unit tests for CommandBus.

Tests command registration, dispatch, middleware, and event handling.
"""

import pytest

from application.common.cqrs import (
    Command,
    CommandBus,
    HandlerNotFoundError,
)
from core.base.patterns.result import Err, Ok, Result


class CreateUserCommand(Command[str, str]):
    """Test command for creating a user."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.events: list[str] = []

    async def execute(self) -> Result[str, str]:
        return Ok(f"User {self.name} created")


class FailingCommand(Command[str, str]):
    """Test command that fails."""

    async def execute(self) -> Result[str, str]:
        return Err("Command failed")


class TestCommandBusRegistration:
    """Tests for command handler registration."""

    def test_register_handler(self) -> None:
        """Test registering a command handler."""
        bus = CommandBus()

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            return Ok(f"Handled {cmd.name}")

        bus.register(CreateUserCommand, handler)
        assert CreateUserCommand in bus._handlers

    def test_register_duplicate_handler_raises(self) -> None:
        """Test that registering duplicate handler raises ValueError."""
        bus = CommandBus()

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            return Ok("OK")

        bus.register(CreateUserCommand, handler)

        with pytest.raises(ValueError, match="Handler already registered"):
            bus.register(CreateUserCommand, handler)

    def test_unregister_handler(self) -> None:
        """Test unregistering a command handler."""
        bus = CommandBus()

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            return Ok("OK")

        bus.register(CreateUserCommand, handler)
        bus.unregister(CreateUserCommand)
        assert CreateUserCommand not in bus._handlers

    def test_unregister_nonexistent_handler(self) -> None:
        """Test unregistering non-existent handler does not raise."""
        bus = CommandBus()
        bus.unregister(CreateUserCommand)  # Should not raise


class TestCommandBusDispatch:
    """Tests for command dispatch."""

    @pytest.mark.asyncio
    async def test_dispatch_command(self) -> None:
        """Test dispatching a command to its handler."""
        bus = CommandBus()
        call_count = 0

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            nonlocal call_count
            call_count += 1
            return Ok(f"Created {cmd.name}")

        bus.register(CreateUserCommand, handler)
        result = await bus.dispatch(CreateUserCommand("John"))

        assert call_count == 1
        assert isinstance(result, Ok)
        assert result.value == "Created John"

    @pytest.mark.asyncio
    async def test_dispatch_unregistered_command_raises(self) -> None:
        """Test dispatching unregistered command raises HandlerNotFoundError."""
        bus = CommandBus()

        with pytest.raises(HandlerNotFoundError):
            await bus.dispatch(CreateUserCommand("John"))

    @pytest.mark.asyncio
    async def test_dispatch_returns_error_result(self) -> None:
        """Test dispatching command that returns error."""
        bus = CommandBus()

        async def handler(cmd: FailingCommand) -> Result[str, str]:
            return Err("Failed")

        bus.register(FailingCommand, handler)
        result = await bus.dispatch(FailingCommand())

        assert isinstance(result, Err)
        assert result.error == "Failed"


class TestCommandBusMiddleware:
    """Tests for middleware functionality."""

    def test_add_middleware(self) -> None:
        """Test adding middleware to bus."""
        bus = CommandBus()

        async def middleware(cmd, next_handler):
            return await next_handler(cmd)

        bus.add_middleware(middleware)
        assert len(bus._middleware) == 1

    def test_add_multiple_middleware(self) -> None:
        """Test adding multiple middleware."""
        bus = CommandBus()

        async def middleware1(cmd, next_handler):
            return await next_handler(cmd)

        async def middleware2(cmd, next_handler):
            return await next_handler(cmd)

        bus.add_middleware(middleware1)
        bus.add_middleware(middleware2)
        assert len(bus._middleware) == 2


class TestCommandBusMiddlewareExecution:
    """Tests for middleware execution behavior."""

    @pytest.mark.asyncio
    async def test_middleware_executes_in_order(self) -> None:
        """Test middleware executes in registration order."""
        bus = CommandBus()
        execution_order: list[str] = []

        async def middleware1(cmd, next_handler):
            execution_order.append("m1_before")
            result = await next_handler(cmd)
            execution_order.append("m1_after")
            return result

        async def middleware2(cmd, next_handler):
            execution_order.append("m2_before")
            result = await next_handler(cmd)
            execution_order.append("m2_after")
            return result

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            execution_order.append("handler")
            return Ok("done")

        bus.add_middleware(middleware1)
        bus.add_middleware(middleware2)
        bus.register(CreateUserCommand, handler)

        await bus.dispatch(CreateUserCommand("Test"))

        assert execution_order == ["m1_before", "m2_before", "handler", "m2_after", "m1_after"]

    @pytest.mark.asyncio
    async def test_middleware_can_modify_result(self) -> None:
        """Test middleware can modify the result."""
        bus = CommandBus()

        async def modifying_middleware(cmd, next_handler):
            result = await next_handler(cmd)
            if isinstance(result, Ok):
                return Ok(f"Modified: {result.value}")
            return result

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            return Ok("original")

        bus.add_middleware(modifying_middleware)
        bus.register(CreateUserCommand, handler)

        result = await bus.dispatch(CreateUserCommand("Test"))

        assert isinstance(result, Ok)
        assert result.value == "Modified: original"

    @pytest.mark.asyncio
    async def test_middleware_can_short_circuit(self) -> None:
        """Test middleware can short-circuit execution."""
        bus = CommandBus()
        handler_called = False

        async def blocking_middleware(cmd, next_handler):
            return Err("Blocked by middleware")

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            nonlocal handler_called
            handler_called = True
            return Ok("done")

        bus.add_middleware(blocking_middleware)
        bus.register(CreateUserCommand, handler)

        result = await bus.dispatch(CreateUserCommand("Test"))

        assert isinstance(result, Err)
        assert result.error == "Blocked by middleware"
        assert not handler_called


class TestCommandBusTransactionMiddleware:
    """Tests for transaction middleware."""

    @pytest.mark.asyncio
    async def test_add_transaction_middleware(self) -> None:
        """Test adding transaction middleware."""
        bus = CommandBus()
        commit_called = False
        close_called = False

        class MockUoW:
            async def commit(self):
                nonlocal commit_called
                commit_called = True

            async def rollback(self):
                pass

            async def close(self):
                nonlocal close_called
                close_called = True

        bus.add_transaction_middleware(MockUoW)

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            return Ok("done")

        bus.register(CreateUserCommand, handler)
        await bus.dispatch(CreateUserCommand("Test"))

        assert commit_called
        assert close_called

    @pytest.mark.asyncio
    async def test_transaction_middleware_rollback_on_exception(self) -> None:
        """Test transaction middleware rolls back on exception."""
        bus = CommandBus()
        rollback_called = False
        close_called = False

        class MockUoW:
            async def commit(self):
                pass

            async def rollback(self):
                nonlocal rollback_called
                rollback_called = True

            async def close(self):
                nonlocal close_called
                close_called = True

        bus.add_transaction_middleware(MockUoW)

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            raise RuntimeError("Handler error")

        bus.register(CreateUserCommand, handler)

        with pytest.raises(RuntimeError, match="Handler error"):
            await bus.dispatch(CreateUserCommand("Test"))

        assert rollback_called
        assert close_called


class TestCommandBusEvents:
    """Tests for event handling."""

    def test_on_event_registers_handler(self) -> None:
        """Test registering event handler."""
        bus = CommandBus()

        async def event_handler(event: str) -> None:
            pass

        bus.on_event(event_handler)
        assert len(bus._event_handlers) == 1

    def test_multiple_event_handlers_registered(self) -> None:
        """Test registering multiple event handlers."""
        bus = CommandBus()

        async def handler1(event: str) -> None:
            pass

        async def handler2(event: str) -> None:
            pass

        bus.on_event(handler1)
        bus.on_event(handler2)
        assert len(bus._event_handlers) == 2

    @pytest.mark.asyncio
    async def test_events_emitted_on_success(self) -> None:
        """Test events are emitted after successful command."""
        bus = CommandBus()
        received_events: list[str] = []

        async def event_handler(event: str) -> None:
            received_events.append(event)

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            cmd.events.append("UserCreated")
            cmd.events.append("WelcomeEmailSent")
            return Ok("done")

        bus.on_event(event_handler)
        bus.register(CreateUserCommand, handler)

        await bus.dispatch(CreateUserCommand("Test"))

        assert received_events == ["UserCreated", "WelcomeEmailSent"]

    @pytest.mark.asyncio
    async def test_events_not_emitted_on_error(self) -> None:
        """Test events are not emitted when command returns error."""
        bus = CommandBus()
        received_events: list[str] = []

        async def event_handler(event: str) -> None:
            received_events.append(event)

        async def handler(cmd: FailingCommand) -> Result[str, str]:
            return Err("Failed")

        bus.on_event(event_handler)
        bus.register(FailingCommand, handler)

        await bus.dispatch(FailingCommand())

        assert received_events == []

    @pytest.mark.asyncio
    async def test_event_handler_error_does_not_fail_dispatch(self) -> None:
        """Test event handler errors don't fail the dispatch."""
        bus = CommandBus()

        async def failing_event_handler(event: str) -> None:
            raise RuntimeError("Event handler failed")

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            cmd.events.append("TestEvent")
            return Ok("done")

        bus.on_event(failing_event_handler)
        bus.register(CreateUserCommand, handler)

        # Should not raise despite event handler failure
        result = await bus.dispatch(CreateUserCommand("Test"))

        assert isinstance(result, Ok)

    @pytest.mark.asyncio
    async def test_events_from_command_object(self) -> None:
        """Test events are extracted from command object."""
        bus = CommandBus()
        received_events: list[str] = []

        async def event_handler(event: str) -> None:
            received_events.append(event)

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            # Events are added to command, not result
            cmd.events.append("EventFromCommand")
            return Ok("done")

        bus.on_event(event_handler)
        bus.register(CreateUserCommand, handler)

        await bus.dispatch(CreateUserCommand("Test"))

        assert received_events == ["EventFromCommand"]

    @pytest.mark.asyncio
    async def test_multiple_event_handlers_all_called(self) -> None:
        """Test all event handlers are called for each event."""
        bus = CommandBus()
        handler1_events: list[str] = []
        handler2_events: list[str] = []

        async def event_handler1(event: str) -> None:
            handler1_events.append(event)

        async def event_handler2(event: str) -> None:
            handler2_events.append(event)

        async def handler(cmd: CreateUserCommand) -> Result[str, str]:
            cmd.events.append("TestEvent")
            return Ok("done")

        bus.on_event(event_handler1)
        bus.on_event(event_handler2)
        bus.register(CreateUserCommand, handler)

        await bus.dispatch(CreateUserCommand("Test"))

        assert handler1_events == ["TestEvent"]
        assert handler2_events == ["TestEvent"]


class TestEmitEventsMethod:
    """Tests for _emit_events internal method."""

    @pytest.mark.asyncio
    async def test_emit_events_returns_empty_list_when_no_events(self) -> None:
        """Test _emit_events returns empty list when no events."""
        bus = CommandBus()

        class NoEventsCommand:
            pass

        errors = await bus._emit_events(NoEventsCommand(), "result")
        assert errors == []

    @pytest.mark.asyncio
    async def test_emit_events_collects_handler_errors(self) -> None:
        """Test _emit_events collects errors from handlers."""
        bus = CommandBus()

        async def failing_handler(event: str) -> None:
            raise ValueError("Handler error")

        bus.on_event(failing_handler)

        class CommandWithEvents:
            events = ["event1", "event2"]

        errors = await bus._emit_events(CommandWithEvents(), "result")

        assert len(errors) == 2
        assert all(isinstance(e, ValueError) for e in errors)

    @pytest.mark.asyncio
    async def test_emit_events_raise_on_error_flag(self) -> None:
        """Test _emit_events raises on first error when flag is set."""
        bus = CommandBus()

        async def failing_handler(event: str) -> None:
            raise ValueError("Handler error")

        bus.on_event(failing_handler)

        class CommandWithEvents:
            events = ["event1"]

        with pytest.raises(ValueError, match="Handler error"):
            await bus._emit_events(
                CommandWithEvents(),
                "result",
                raise_on_error=True,
            )
