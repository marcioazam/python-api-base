"""Dependency Injection Container with PEP 695 type parameters.

This module has been refactored into smaller, focused modules:
- di/exceptions.py: DI-specific exceptions
- di/lifecycle.py: Lifetime enum and Registration dataclass
- di/resolver.py: Dependency resolution logic
- di/scopes.py: Scope class for scoped dependencies

This file now contains the main Container class and serves as a compatibility layer.

**Feature: generics-100-percent-fixes**
**Validates: Requirements 28.1, 28.2, 28.3, 4.1, 4.2, 4.3, 4.4, 4.5**
**Refactored: 2025 - Split 447 lines into 4 focused modules**
"""

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from .exceptions import (
    CircularDependencyError,
    DependencyResolutionError,
    InvalidFactoryError,
    ServiceNotRegisteredError,
)
from .lifecycle import Lifetime, Registration
from .resolver import Resolver
from .scopes import Scope

# Re-export for backward compatibility
__all__ = [
    # Exceptions
    "DependencyResolutionError",
    "CircularDependencyError",
    "InvalidFactoryError",
    "ServiceNotRegisteredError",
    # Lifecycle
    "Lifetime",
    "Registration",
    # Container
    "Container",
    # Scope
    "Scope",
]


class Container:
    """Type-safe dependency injection container with proper error handling.

    Features:
        - Auto-wiring: Automatically resolves constructor dependencies
        - Lifetime management: TRANSIENT, SINGLETON, SCOPED
        - Circular dependency detection
        - Type-safe with PEP 695 generics
        - Scoped containers for request-scoped dependencies

    **Feature: generics-100-percent-fixes**
    **Validates: Requirements 28.1, 28.2, 28.3, 4.1, 4.2, 4.3, 4.4, 4.5**

    Example:
        >>> container = Container()
        >>> container.register(Database, lifetime=Lifetime.SINGLETON)
        >>> container.register(UserService)  # Auto-wires Database dependency
        >>> service = container.resolve(UserService)
    """

    def __init__(self) -> None:
        """Initialize container."""
        self._registrations: dict[type, Registration[Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._resolution_stack: list[type] = []
        self._resolver = Resolver(self._registrations, self.resolve)

    def register[T](
        self,
        service_type: type[T],
        factory: Callable[..., T] | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> None:
        """Register a service with the container.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 28.1**

        Args:
            service_type: The type to register.
            factory: Factory function to create instances. If None, uses service_type.
            lifetime: Lifetime of the service (TRANSIENT, SINGLETON, SCOPED).

        Raises:
            InvalidFactoryError: If factory is not callable or has invalid signature.

        Example:
            >>> container.register(Database, lifetime=Lifetime.SINGLETON)
            >>> container.register(UserService, lambda: UserService(db))
        """
        if factory is None:
            factory = service_type

        # Validate factory
        self._resolver.validate_factory(factory, service_type)

        self._registrations[service_type] = Registration(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime,
        )

    def register_singleton[T](
        self,
        service_type: type[T],
        factory: Callable[..., T] | None = None,
    ) -> None:
        """Register a singleton service.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 28.2**

        Args:
            service_type: The type to register.
            factory: Factory function to create the instance.

        Example:
            >>> container.register_singleton(Database)
        """
        self.register(service_type, factory, Lifetime.SINGLETON)

    def register_scoped[T](
        self,
        service_type: type[T],
        factory: Callable[..., T] | None = None,
    ) -> None:
        """Register a scoped service.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 28.3**

        Args:
            service_type: The type to register.
            factory: Factory function to create instances.

        Example:
            >>> container.register_scoped(UnitOfWork)
        """
        self.register(service_type, factory, Lifetime.SCOPED)

    def register_instance[T](
        self,
        service_type: type[T],
        instance: T,
    ) -> None:
        """Register an existing instance as singleton.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 28.2**

        Args:
            service_type: The type to register.
            instance: The instance to register.

        Example:
            >>> db = Database()
            >>> container.register_instance(Database, db)
        """
        self._registrations[service_type] = Registration(
            service_type=service_type,
            factory=lambda: instance,
            lifetime=Lifetime.SINGLETON,
            instance=instance,
        )
        self._singletons[service_type] = instance

    def resolve[T](self, service_type: type[T]) -> T:
        """Resolve a service from the container.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 4.1, 4.2, 4.3**

        Args:
            service_type: The type to resolve.

        Returns:
            Instance of the requested type.

        Raises:
            ServiceNotRegisteredError: If service is not registered.
            CircularDependencyError: If circular dependency detected.
            DependencyResolutionError: If dependency cannot be resolved.

        Example:
            >>> service = container.resolve(UserService)
        """
        if service_type not in self._registrations:
            raise ServiceNotRegisteredError(service_type)

        # Check for circular dependency
        if service_type in self._resolution_stack:
            chain = self._resolution_stack + [service_type]
            raise CircularDependencyError(chain)

        registration = self._registrations[service_type]

        if registration.lifetime == Lifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]

            self._resolution_stack.append(service_type)
            try:
                instance = self._resolver.create_instance(registration)
            finally:
                self._resolution_stack.pop()

            self._singletons[service_type] = instance
            return instance

        self._resolution_stack.append(service_type)
        try:
            return self._resolver.create_instance(registration)
        finally:
            self._resolution_stack.pop()

    def is_registered(self, service_type: type) -> bool:
        """Check if a service is registered.

        Args:
            service_type: The type to check.

        Returns:
            True if registered, False otherwise.

        Example:
            >>> if container.is_registered(Database):
            ...     db = container.resolve(Database)
        """
        return service_type in self._registrations

    @contextmanager
    def create_scope(self):
        """Create a new scope for scoped dependencies.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 28.3**

        Yields:
            Scope: A new scope instance.

        Example:
            >>> with container.create_scope() as scope:
            ...     uow = scope.resolve(UnitOfWork)
            ...     # Use uow within this scope
            ...     # Automatically disposed when exiting context
        """
        scope = Scope(self)
        try:
            yield scope
        finally:
            scope.dispose()
