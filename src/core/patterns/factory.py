"""Generic Factory pattern implementation.

Provides a type-safe factory for creating instances with DI support.
Uses PEP 695 type parameter syntax.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class Factory[T](ABC):
    """Abstract factory for creating instances of type T.

    Type Parameters:
        T: The type of objects this factory creates.
    """

    @abstractmethod
    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create a new instance.

        Args:
            *args: Positional arguments for creation.
            **kwargs: Keyword arguments for creation.

        Returns:
            New instance of type T.
        """
        ...


class SimpleFactory[T](Factory[T]):
    """Simple factory using a callable creator.

    Type Parameters:
        T: The type of objects this factory creates.

    Example:
        >>> factory = SimpleFactory(User)
        >>> user = factory.create(name="John", email="john@example.com")
    """

    def __init__(self, creator: Callable[..., T]) -> None:
        """Initialize factory with creator callable.

        Args:
            creator: Callable that creates instances of T.
        """
        self._creator = creator

    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create a new instance using the creator."""
        return self._creator(*args, **kwargs)


class RegistryFactory[TKey, T]:
    """Factory with registered creators by key.

    Type Parameters:
        TKey: The type of keys used to identify creators.
        T: The base type of objects this factory creates.

    Example:
        >>> factory = RegistryFactory[str, Notification]()
        >>> factory.register("email", EmailNotification)
        >>> factory.register("sms", SMSNotification)
        >>> notification = factory.create("email", recipient="user@example.com")
    """

    def __init__(self) -> None:
        self._creators: dict[TKey, Callable[..., T]] = {}

    def register(self, key: TKey, creator: Callable[..., T]) -> None:
        """Register a creator for a key.

        Args:
            key: Key to identify this creator.
            creator: Callable that creates instances.
        """
        self._creators[key] = creator

    def unregister(self, key: TKey) -> None:
        """Unregister a creator.

        Args:
            key: Key of the creator to remove.
        """
        self._creators.pop(key, None)

    def create(self, key: TKey, *args: Any, **kwargs: Any) -> T:
        """Create an instance using the registered creator.

        Args:
            key: Key identifying which creator to use.
            *args: Positional arguments for creation.
            **kwargs: Keyword arguments for creation.

        Returns:
            New instance of type T.

        Raises:
            KeyError: If no creator is registered for the key.
        """
        if key not in self._creators:
            raise KeyError(f"No creator registered for key: {key}")
        return self._creators[key](*args, **kwargs)

    def has_creator(self, key: TKey) -> bool:
        """Check if a creator is registered for a key."""
        return key in self._creators

    @property
    def registered_keys(self) -> list[TKey]:
        """Get list of registered keys."""
        return list(self._creators.keys())


class SingletonFactory[T](Factory[T]):
    """Factory that returns the same instance (singleton).

    Type Parameters:
        T: The type of the singleton object.

    Example:
        >>> factory = SingletonFactory(lambda: DatabaseConnection())
        >>> conn1 = factory.create()
        >>> conn2 = factory.create()
        >>> assert conn1 is conn2
    """

    def __init__(self, creator: Callable[[], T]) -> None:
        """Initialize factory with creator callable.

        Args:
            creator: Callable that creates the singleton instance.
        """
        self._creator = creator
        self._instance: T | None = None

    def create(self, *args: Any, **kwargs: Any) -> T:
        """Get or create the singleton instance."""
        if self._instance is None:
            self._instance = self._creator()
        return self._instance

    def reset(self) -> None:
        """Reset the singleton (for testing)."""
        self._instance = None


class PooledFactory[T]:
    """Factory that manages a pool of reusable instances.

    Type Parameters:
        T: The type of objects in the pool.

    Example:
        >>> factory = PooledFactory(create_connection, max_size=10)
        >>> conn = factory.acquire()
        >>> # use connection
        >>> factory.release(conn)
    """

    def __init__(
        self,
        creator: Callable[[], T],
        max_size: int = 10,
        validator: Callable[[T], bool] | None = None,
    ) -> None:
        """Initialize pooled factory.

        Args:
            creator: Callable that creates new instances.
            max_size: Maximum pool size.
            validator: Optional function to validate instances before reuse.
        """
        self._creator = creator
        self._max_size = max_size
        self._validator = validator
        self._pool: list[T] = []
        self._in_use: set[int] = set()

    def acquire(self) -> T:
        """Acquire an instance from the pool.

        Returns:
            Instance from pool or newly created.
        """
        # Try to get from pool
        while self._pool:
            instance = self._pool.pop()
            if self._validator is None or self._validator(instance):
                self._in_use.add(id(instance))
                return instance

        # Create new instance
        instance = self._creator()
        self._in_use.add(id(instance))
        return instance

    def release(self, instance: T) -> None:
        """Release an instance back to the pool.

        Args:
            instance: Instance to release.
        """
        instance_id = id(instance)
        if instance_id in self._in_use:
            self._in_use.remove(instance_id)
            if len(self._pool) < self._max_size:
                self._pool.append(instance)

    @property
    def pool_size(self) -> int:
        """Get current pool size."""
        return len(self._pool)

    @property
    def in_use_count(self) -> int:
        """Get count of instances in use."""
        return len(self._in_use)
