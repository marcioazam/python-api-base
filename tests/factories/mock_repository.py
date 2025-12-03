"""Mock repository factories for testing.

Provides type-safe mock implementations for testing repository-dependent code.

**Feature: api-architecture-analysis, Task 4.3: Type-safe Mocks**
**Validates: Requirements 8.1**

Usage:
    from tests.factories.mock_repository import (
        MockRepository,
        MockRepositoryFactory,
        TypedMock,
        create_typed_mock,
    )

    # Create a type-safe mock repository
    mock_repo = MockRepository[Item, ItemCreate, ItemUpdate](Item)

    # Create a typed mock for any interface
    mock_service = create_typed_mock(IUserService)
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, ParamSpec, Protocol, TypeVar, cast, overload
from unittest.mock import AsyncMock, MagicMock, Mock

from pydantic import BaseModel

from core.base.repository import IRepository

T = TypeVar("T", bound=BaseModel)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)
P = ParamSpec("P")
R = TypeVar("R")


class MockRepository(IRepository[T, CreateT, UpdateT], Generic[T, CreateT, UpdateT]):
    """Configurable mock repository for testing.
    
    Allows configuring return values and behaviors for each method.
    """

    def __init__(
        self,
        entity_type: type[T],
        *,
        get_by_id_return: T | None = None,
        get_all_return: tuple[Sequence[T], int] | None = None,
        create_return: T | None = None,
        update_return: T | None = None,
        delete_return: bool = True,
        exists_return: bool = True,
        create_many_return: Sequence[T] | None = None,
        raise_on_create: Exception | None = None,
        raise_on_update: Exception | None = None,
        raise_on_delete: Exception | None = None,
    ) -> None:
        """Initialize mock repository with configurable behavior.
        
        Args:
            entity_type: Type of entity this repository handles.
            get_by_id_return: Value to return from get_by_id.
            get_all_return: Value to return from get_all.
            create_return: Value to return from create.
            update_return: Value to return from update.
            delete_return: Value to return from delete.
            exists_return: Value to return from exists.
            create_many_return: Value to return from create_many.
            raise_on_create: Exception to raise on create.
            raise_on_update: Exception to raise on update.
            raise_on_delete: Exception to raise on delete.
        """
        self._entity_type = entity_type
        self._get_by_id_return = get_by_id_return
        self._get_all_return = get_all_return or ([], 0)
        self._create_return = create_return
        self._update_return = update_return
        self._delete_return = delete_return
        self._exists_return = exists_return
        self._create_many_return = create_many_return or []
        self._raise_on_create = raise_on_create
        self._raise_on_update = raise_on_update
        self._raise_on_delete = raise_on_delete
        
        # Track calls
        self.get_by_id_calls: list[str] = []
        self.get_all_calls: list[dict[str, Any]] = []
        self.create_calls: list[CreateT] = []
        self.update_calls: list[tuple[str, UpdateT]] = []
        self.delete_calls: list[str] = []
        self.exists_calls: list[str] = []
        self.create_many_calls: list[Sequence[CreateT]] = []

    async def get_by_id(self, id: str) -> T | None:
        """Get entity by ID."""
        self.get_by_id_calls.append(id)
        return self._get_by_id_return

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[Sequence[T], int]:
        """Get paginated list of entities."""
        self.get_all_calls.append({
            "skip": skip,
            "limit": limit,
            "filters": filters,
            "sort_by": sort_by,
            "sort_order": sort_order,
        })
        return self._get_all_return

    async def create(self, data: CreateT) -> T:
        """Create new entity."""
        self.create_calls.append(data)
        if self._raise_on_create:
            raise self._raise_on_create
        if self._create_return:
            return self._create_return
        # Create a default entity from the data
        return self._entity_type.model_validate(data.model_dump())

    async def update(self, id: str, data: UpdateT) -> T | None:
        """Update existing entity."""
        self.update_calls.append((id, data))
        if self._raise_on_update:
            raise self._raise_on_update
        return self._update_return

    async def delete(self, id: str, *, soft: bool = True) -> bool:
        """Delete entity."""
        self.delete_calls.append(id)
        if self._raise_on_delete:
            raise self._raise_on_delete
        return self._delete_return

    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]:
        """Bulk create entities."""
        self.create_many_calls.append(data)
        if self._create_many_return:
            return self._create_many_return
        return [self._entity_type.model_validate(d.model_dump()) for d in data]

    async def exists(self, id: str) -> bool:
        """Check if entity exists."""
        self.exists_calls.append(id)
        return self._exists_return

    def reset_calls(self) -> None:
        """Reset all call tracking."""
        self.get_by_id_calls.clear()
        self.get_all_calls.clear()
        self.create_calls.clear()
        self.update_calls.clear()
        self.delete_calls.clear()
        self.exists_calls.clear()
        self.create_many_calls.clear()


class MockRepositoryFactory:
    """Factory for creating mock repositories with common configurations."""

    @staticmethod
    def create_empty(entity_type: type[T]) -> MockRepository[T, Any, Any]:
        """Create a mock repository that returns empty/None for all queries."""
        return MockRepository(
            entity_type,
            get_by_id_return=None,
            get_all_return=([], 0),
            update_return=None,
            delete_return=False,
            exists_return=False,
        )

    @staticmethod
    def create_with_entity(
        entity_type: type[T],
        entity: T,
    ) -> MockRepository[T, Any, Any]:
        """Create a mock repository that returns the given entity."""
        return MockRepository(
            entity_type,
            get_by_id_return=entity,
            get_all_return=([entity], 1),
            create_return=entity,
            update_return=entity,
            delete_return=True,
            exists_return=True,
        )

    @staticmethod
    def create_with_entities(
        entity_type: type[T],
        entities: list[T],
    ) -> MockRepository[T, Any, Any]:
        """Create a mock repository with multiple entities."""
        return MockRepository(
            entity_type,
            get_by_id_return=entities[0] if entities else None,
            get_all_return=(entities, len(entities)),
            create_return=entities[0] if entities else None,
            update_return=entities[0] if entities else None,
            delete_return=True,
            exists_return=bool(entities),
            create_many_return=entities,
        )

    @staticmethod
    def create_failing(
        entity_type: type[T],
        exception: Exception,
    ) -> MockRepository[T, Any, Any]:
        """Create a mock repository that raises exceptions."""
        return MockRepository(
            entity_type,
            raise_on_create=exception,
            raise_on_update=exception,
            raise_on_delete=exception,
        )


# =============================================================================
# Type-Safe Mock Wrapper
# =============================================================================


@dataclass
class CallRecord(Generic[P, R]):
    """Record of a single method call with typed arguments and return value."""

    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    return_value: R | None = None
    exception: Exception | None = None


@dataclass
class MethodCallTracker(Generic[P, R]):
    """Tracks calls to a specific method with type information."""

    calls: list[CallRecord[P, R]] = field(default_factory=list)

    @property
    def call_count(self) -> int:
        """Number of times the method was called."""
        return len(self.calls)

    @property
    def called(self) -> bool:
        """Whether the method was called at least once."""
        return len(self.calls) > 0

    @property
    def last_call(self) -> CallRecord[P, R] | None:
        """The most recent call, or None if never called."""
        return self.calls[-1] if self.calls else None

    def assert_called(self) -> None:
        """Assert that the method was called at least once."""
        if not self.called:
            raise AssertionError("Method was not called")

    def assert_called_once(self) -> None:
        """Assert that the method was called exactly once."""
        if self.call_count != 1:
            raise AssertionError(f"Method was called {self.call_count} times, expected 1")

    def assert_called_with(self, *args: Any, **kwargs: Any) -> None:
        """Assert that the last call had the specified arguments."""
        if not self.called:
            raise AssertionError("Method was not called")
        last = self.last_call
        if last is None:
            raise AssertionError("No calls recorded")
        if last.args != args or last.kwargs != kwargs:
            raise AssertionError(
                f"Expected call with args={args}, kwargs={kwargs}, "
                f"got args={last.args}, kwargs={last.kwargs}"
            )

    def reset(self) -> None:
        """Clear all recorded calls."""
        self.calls.clear()


class TypedMock(Generic[T]):
    """Type-safe mock wrapper that preserves interface type information.

    Wraps a MagicMock or AsyncMock while providing type hints for the
    mocked interface. This enables IDE autocompletion and type checking
    while still allowing mock configuration.

    Type Parameters:
        T: The interface type being mocked.

    Example:
        >>> mock = TypedMock[IUserService]()
        >>> mock.configure_method("get_user", return_value=user)
        >>> result = await mock.instance.get_user("123")
    """

    def __init__(
        self,
        interface_type: type[T] | None = None,
        *,
        spec: type[T] | None = None,
        use_async: bool = True,
    ) -> None:
        """Initialize typed mock.

        Args:
            interface_type: The interface type being mocked (for documentation).
            spec: Optional spec to use for the mock (enables attribute checking).
            use_async: Whether to use AsyncMock (True) or MagicMock (False).
        """
        self._interface_type = interface_type or spec
        mock_class = AsyncMock if use_async else MagicMock
        self._mock = mock_class(spec=spec) if spec else mock_class()
        self._method_trackers: dict[str, MethodCallTracker[Any, Any]] = {}
        self._configured_returns: dict[str, Any] = {}
        self._configured_side_effects: dict[str, Any] = {}

    @property
    def instance(self) -> T:
        """Get the mock instance typed as the interface.

        Returns:
            The mock cast to the interface type for type-safe usage.
        """
        return cast(T, self._mock)

    @property
    def mock(self) -> MagicMock | AsyncMock:
        """Get the underlying mock for advanced configuration."""
        return self._mock

    def configure_method(
        self,
        method_name: str,
        *,
        return_value: Any = None,
        side_effect: Any = None,
    ) -> "TypedMock[T]":
        """Configure a method's return value or side effect.

        Args:
            method_name: Name of the method to configure.
            return_value: Value to return when the method is called.
            side_effect: Side effect (exception or callable) for the method.

        Returns:
            Self for method chaining.
        """
        method_mock = getattr(self._mock, method_name)
        if return_value is not None:
            method_mock.return_value = return_value
            self._configured_returns[method_name] = return_value
        if side_effect is not None:
            method_mock.side_effect = side_effect
            self._configured_side_effects[method_name] = side_effect
        return self

    def configure_async_method(
        self,
        method_name: str,
        *,
        return_value: Any = None,
        side_effect: Any = None,
    ) -> "TypedMock[T]":
        """Configure an async method's return value or side effect.

        For async methods, the return_value is automatically wrapped
        in an awaitable.

        Args:
            method_name: Name of the async method to configure.
            return_value: Value to return when awaited.
            side_effect: Side effect (exception or callable) for the method.

        Returns:
            Self for method chaining.
        """
        method_mock = getattr(self._mock, method_name)
        if return_value is not None:
            method_mock.return_value = return_value
            self._configured_returns[method_name] = return_value
        if side_effect is not None:
            method_mock.side_effect = side_effect
            self._configured_side_effects[method_name] = side_effect
        return self

    def get_tracker(self, method_name: str) -> MethodCallTracker[Any, Any]:
        """Get the call tracker for a specific method.

        Args:
            method_name: Name of the method to track.

        Returns:
            MethodCallTracker for the specified method.
        """
        if method_name not in self._method_trackers:
            self._method_trackers[method_name] = MethodCallTracker()
        return self._method_trackers[method_name]

    def assert_method_called(self, method_name: str) -> None:
        """Assert that a method was called."""
        method_mock = getattr(self._mock, method_name)
        method_mock.assert_called()

    def assert_method_called_once(self, method_name: str) -> None:
        """Assert that a method was called exactly once."""
        method_mock = getattr(self._mock, method_name)
        method_mock.assert_called_once()

    def assert_method_called_with(
        self, method_name: str, *args: Any, **kwargs: Any
    ) -> None:
        """Assert that a method was called with specific arguments."""
        method_mock = getattr(self._mock, method_name)
        method_mock.assert_called_with(*args, **kwargs)

    def reset_mock(self) -> None:
        """Reset the mock and all trackers."""
        self._mock.reset_mock()
        for tracker in self._method_trackers.values():
            tracker.reset()


def create_typed_mock(
    interface_type: type[T],
    *,
    use_async: bool = True,
    **method_returns: Any,
) -> TypedMock[T]:
    """Create a typed mock for an interface with optional method configurations.

    Args:
        interface_type: The interface type to mock.
        use_async: Whether to use AsyncMock (True) or MagicMock (False).
        **method_returns: Method name to return value mappings.

    Returns:
        A TypedMock configured with the specified return values.

    Example:
        >>> mock = create_typed_mock(
        ...     IUserService,
        ...     get_user=user,
        ...     list_users=[user1, user2],
        ... )
    """
    typed_mock = TypedMock[T](interface_type, use_async=use_async)
    for method_name, return_value in method_returns.items():
        typed_mock.configure_method(method_name, return_value=return_value)
    return typed_mock
