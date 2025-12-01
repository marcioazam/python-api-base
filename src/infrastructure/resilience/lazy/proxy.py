"""Lazy loading proxy classes.

**Feature: file-size-compliance-phase2, Task 2.5**
**Validates: Requirements 1.5, 5.1, 5.2, 5.3**
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from .enums import LoadState


@dataclass
class LazyProxy[T]:
    """Generic lazy loading proxy for deferred value loading."""

    loader: Callable[[], T | Awaitable[T]]
    _value: T | None = field(default=None, init=False, repr=False)
    _state: LoadState = field(default=LoadState.NOT_LOADED, init=False)
    _error: Exception | None = field(default=None, init=False, repr=False)

    @property
    def is_loaded(self) -> bool:
        """Check if the value has been loaded."""
        return self._state == LoadState.LOADED

    @property
    def is_loading(self) -> bool:
        """Check if the value is currently being loaded."""
        return self._state == LoadState.LOADING

    @property
    def has_error(self) -> bool:
        """Check if loading resulted in an error."""
        return self._state == LoadState.ERROR

    @property
    def state(self) -> LoadState:
        """Get the current loading state."""
        return self._state

    async def get(self, timeout: float | None = None) -> T:
        """Get the value, loading it if necessary.

        Args:
            timeout: Optional timeout in seconds. If exceeded, raises TimeoutError.

        Returns:
            The loaded value.

        Raises:
            TimeoutError: If timeout is exceeded during loading.
        """
        if self._state == LoadState.LOADED:
            return self._value  # type: ignore

        if self._state == LoadState.ERROR and self._error:
            raise self._error

        self._state = LoadState.LOADING
        try:
            result = self.loader()
            if isinstance(result, Awaitable):
                if timeout is not None:
                    try:
                        self._value = await asyncio.wait_for(result, timeout=timeout)
                    except asyncio.TimeoutError:
                        self._state = LoadState.ERROR
                        self._error = TimeoutError(
                            f"LazyProxy loading exceeded timeout of {timeout} seconds"
                        )
                        raise self._error
                else:
                    self._value = await result
            else:
                self._value = result
            self._state = LoadState.LOADED
            return self._value
        except TimeoutError:
            raise
        except Exception as e:
            self._state = LoadState.ERROR
            self._error = e
            raise

    def get_sync(self) -> T:
        """Get the value synchronously (for sync loaders only)."""
        if self._state == LoadState.LOADED:
            return self._value  # type: ignore

        if self._state == LoadState.ERROR and self._error:
            raise self._error

        self._state = LoadState.LOADING
        try:
            result = self.loader()
            if isinstance(result, Awaitable):
                raise RuntimeError("Cannot use get_sync() with async loader")
            self._value = result
            self._state = LoadState.LOADED
            return self._value
        except Exception as e:
            self._state = LoadState.ERROR
            self._error = e
            raise

    def get_if_loaded(self) -> T | None:
        """Get the value only if already loaded."""
        if self._state == LoadState.LOADED:
            return self._value
        return None

    def reset(self) -> None:
        """Reset the proxy to unloaded state."""
        self._value = None
        self._state = LoadState.NOT_LOADED
        self._error = None

    def reload(self) -> "LazyProxy[T]":
        """Create a new proxy that will reload the value."""
        return LazyProxy(self.loader)


@dataclass
class LazyCollection[T]:
    """Lazy loading collection for deferred batch loading."""

    loader: Callable[[], list[T] | Awaitable[list[T]]]
    _items: list[T] = field(default_factory=list, init=False, repr=False)
    _state: LoadState = field(default=LoadState.NOT_LOADED, init=False)
    _error: Exception | None = field(default=None, init=False, repr=False)

    @property
    def is_loaded(self) -> bool:
        """Check if the collection has been loaded."""
        return self._state == LoadState.LOADED

    async def get_all(self) -> list[T]:
        """Get all items, loading if necessary."""
        if self._state == LoadState.LOADED:
            return self._items

        if self._state == LoadState.ERROR and self._error:
            raise self._error

        self._state = LoadState.LOADING
        try:
            result = self.loader()
            if isinstance(result, Awaitable):
                self._items = await result
            else:
                self._items = result
            self._state = LoadState.LOADED
            return self._items
        except Exception as e:
            self._state = LoadState.ERROR
            self._error = e
            raise

    async def get_first(self) -> T | None:
        """Get the first item, loading if necessary."""
        items = await self.get_all()
        return items[0] if items else None

    async def count(self) -> int:
        """Get the count of items, loading if necessary."""
        items = await self.get_all()
        return len(items)

    def reset(self) -> None:
        """Reset the collection to unloaded state."""
        self._items = []
        self._state = LoadState.NOT_LOADED
        self._error = None


@dataclass
class LazyRef[T]:
    """Lazy reference to a related entity by ID."""

    id: str
    resolver: Callable[[str], Awaitable[T | None]]
    _value: T | None = field(default=None, init=False, repr=False)
    _resolved: bool = field(default=False, init=False)

    @property
    def is_resolved(self) -> bool:
        """Check if the reference has been resolved."""
        return self._resolved

    async def resolve(self) -> T | None:
        """Resolve the reference to get the actual entity."""
        if self._resolved:
            return self._value

        self._value = await self.resolver(self.id)
        self._resolved = True
        return self._value

    def get_if_resolved(self) -> T | None:
        """Get the value only if already resolved."""
        return self._value if self._resolved else None

    def reset(self) -> None:
        """Reset the reference to unresolved state."""
        self._value = None
        self._resolved = False
