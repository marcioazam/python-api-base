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

import logging
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)

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
    "ContainerStats",
    "ContainerHooks",
    # Scope
    "Scope",
]


@dataclass
class ContainerStats:
    """Statistics about container usage for observability.

    Tracks registration and resolution metrics to provide insight into
    container behavior and performance characteristics.

    Attributes:
        total_registrations: Total number of services registered.
        singleton_registrations: Number of singleton services.
        transient_registrations: Number of transient services.
        scoped_registrations: Number of scoped services.
        total_resolutions: Total number of service resolutions.
        singleton_instances_created: Number of singleton instances created.
        resolutions_by_type: Count of resolutions per service type.

    Example:
        >>> stats = container.get_stats()
        >>> print(f"Total registrations: {stats.total_registrations}")
        >>> print(f"Singletons created: {stats.singleton_instances_created}")
        >>> print(f"Resolution count for UserService: {stats.resolutions_by_type.get(UserService, 0)}")
    """

    total_registrations: int = 0
    singleton_registrations: int = 0
    transient_registrations: int = 0
    scoped_registrations: int = 0
    total_resolutions: int = 0
    singleton_instances_created: int = 0
    resolutions_by_type: dict[str, int] = field(default_factory=dict)


class ContainerHooks(Protocol):
    """Protocol for container observability hooks.

    Hooks allow external systems to be notified of container events
    for logging, monitoring, and debugging purposes.

    All hook methods are optional and should not raise exceptions.
    If a hook raises an exception, it will be caught and logged.

    Example:
        >>> class LoggingHooks:
        ...     def on_service_registered(self, service_type: type, lifetime: Lifetime) -> None:
        ...         logger.info(f"Registered {service_type.__name__} as {lifetime}")
        ...
        ...     def on_service_resolved(self, service_type: type, instance: Any) -> None:
        ...         logger.debug(f"Resolved {service_type.__name__}")
        ...
        >>> container = Container()
        >>> container.add_hooks(LoggingHooks())
    """

    def on_service_registered(
        self, service_type: type, lifetime: Lifetime, factory: Callable | None
    ) -> None:
        """Called when a service is registered.

        Args:
            service_type: The type being registered.
            lifetime: The lifetime of the service.
            factory: The factory function (if provided).
        """
        ...

    def on_service_resolved(
        self, service_type: type, instance: Any, is_cached: bool
    ) -> None:
        """Called when a service is successfully resolved.

        Args:
            service_type: The type that was resolved.
            instance: The resolved instance.
            is_cached: Whether the instance came from cache (singleton).
        """
        ...

    def on_resolution_error(
        self, service_type: type, error: Exception, resolution_stack: list[type]
    ) -> None:
        """Called when service resolution fails.

        Args:
            service_type: The type that failed to resolve.
            error: The exception that occurred.
            resolution_stack: The current resolution chain when error occurred.
        """
        ...


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
        """Initialize container with metrics tracking and observability hooks."""
        self._registrations: dict[type, Registration[Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._resolution_stack: list[type] = []
        self._resolver = Resolver(self._registrations, self.resolve)

        # Metrics tracking
        self._metrics = ContainerStats()
        self._singleton_instances_created: set[type] = set()

        # Observability hooks
        self._hooks: list[ContainerHooks] = []

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

        # Track metrics
        self._metrics.total_registrations += 1
        if lifetime == Lifetime.SINGLETON:
            self._metrics.singleton_registrations += 1
        elif lifetime == Lifetime.SCOPED:
            self._metrics.scoped_registrations += 1
        elif lifetime == Lifetime.TRANSIENT:
            self._metrics.transient_registrations += 1

        # Trigger observability hooks
        self._trigger_hook(
            "on_service_registered",
            service_type=service_type,
            lifetime=lifetime,
            factory=factory,
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

        # Track metrics
        self._metrics.total_registrations += 1
        self._metrics.singleton_registrations += 1
        self._singleton_instances_created.add(service_type)
        self._metrics.singleton_instances_created = len(self._singleton_instances_created)

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
        try:
            if service_type not in self._registrations:
                raise ServiceNotRegisteredError(service_type)

            # Check for circular dependency
            if service_type in self._resolution_stack:
                chain = self._resolution_stack + [service_type]
                raise CircularDependencyError(chain)
        except Exception as e:
            # Trigger error hook for early failures (not registered, circular dependency)
            self._trigger_hook(
                "on_resolution_error",
                service_type=service_type,
                error=e,
                resolution_stack=self._resolution_stack.copy(),
            )
            raise

        registration = self._registrations[service_type]

        # Track resolution attempt
        self._metrics.total_resolutions += 1
        type_name = service_type.__name__
        self._metrics.resolutions_by_type[type_name] = (
            self._metrics.resolutions_by_type.get(type_name, 0) + 1
        )

        if registration.lifetime == Lifetime.SINGLETON:
            if service_type in self._singletons:
                instance = self._singletons[service_type]
                # Trigger hook for cached resolution
                self._trigger_hook(
                    "on_service_resolved",
                    service_type=service_type,
                    instance=instance,
                    is_cached=True,
                )
                return instance

            self._resolution_stack.append(service_type)
            try:
                instance = self._resolver.create_instance(registration)
            except Exception as e:
                # Trigger error hook
                self._trigger_hook(
                    "on_resolution_error",
                    service_type=service_type,
                    error=e,
                    resolution_stack=self._resolution_stack.copy(),
                )
                raise
            finally:
                self._resolution_stack.pop()

            self._singletons[service_type] = instance

            # Track singleton instance creation
            if service_type not in self._singleton_instances_created:
                self._singleton_instances_created.add(service_type)
                self._metrics.singleton_instances_created = len(
                    self._singleton_instances_created
                )

            # Trigger hook for new singleton creation
            self._trigger_hook(
                "on_service_resolved",
                service_type=service_type,
                instance=instance,
                is_cached=False,
            )

            return instance

        self._resolution_stack.append(service_type)
        try:
            instance = self._resolver.create_instance(registration)
            # Trigger hook for transient/scoped resolution
            self._trigger_hook(
                "on_service_resolved",
                service_type=service_type,
                instance=instance,
                is_cached=False,
            )
            return instance
        except Exception as e:
            # Trigger error hook
            self._trigger_hook(
                "on_resolution_error",
                service_type=service_type,
                error=e,
                resolution_stack=self._resolution_stack.copy(),
            )
            raise
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

    def get_stats(self) -> ContainerStats:
        """Get container usage statistics for observability.

        **Feature: di-observability**
        **Validates: Requirements for container monitoring and debugging**

        Returns:
            ContainerStats: Current statistics snapshot including:
                - Registration counts by lifetime
                - Resolution counts overall and by type
                - Singleton instances created

        Example:
            >>> stats = container.get_stats()
            >>> print(f"Total registrations: {stats.total_registrations}")
            >>> print(f"Singletons: {stats.singleton_registrations}")
            >>> print(f"Total resolutions: {stats.total_resolutions}")
            >>> print(f"UserService resolutions: {stats.resolutions_by_type.get('UserService', 0)}")

            >>> # Check for potential issues
            >>> if stats.total_resolutions > 1000 * stats.total_registrations:
            ...     logger.warning("High resolution count - consider singletons")
        """
        # Return a copy to prevent external mutation
        return ContainerStats(
            total_registrations=self._metrics.total_registrations,
            singleton_registrations=self._metrics.singleton_registrations,
            transient_registrations=self._metrics.transient_registrations,
            scoped_registrations=self._metrics.scoped_registrations,
            total_resolutions=self._metrics.total_resolutions,
            singleton_instances_created=self._metrics.singleton_instances_created,
            resolutions_by_type=self._metrics.resolutions_by_type.copy(),
        )

    def add_hooks(self, hooks: ContainerHooks) -> None:
        """Add observability hooks to the container.

        **Feature: di-observability**
        **Validates: Requirements for external monitoring integration**

        Args:
            hooks: An object implementing the ContainerHooks protocol.

        Example:
            >>> class LoggingHooks:
            ...     def on_service_registered(self, service_type, lifetime, factory):
            ...         logger.info(f"Registered {service_type.__name__}")
            ...     def on_service_resolved(self, service_type, instance, is_cached):
            ...         logger.debug(f"Resolved {service_type.__name__}")
            ...     def on_resolution_error(self, service_type, error, resolution_stack):
            ...         logger.error(f"Failed to resolve {service_type.__name__}: {error}")
            >>>
            >>> container = Container()
            >>> container.add_hooks(LoggingHooks())
        """
        self._hooks.append(hooks)

    def _trigger_hook(
        self, hook_name: str, *args: Any, **kwargs: Any
    ) -> None:
        """Trigger all registered hooks for a specific event.

        Hook exceptions are caught and logged to prevent hooks from breaking container operation.

        Args:
            hook_name: Name of the hook method to call.
            *args: Positional arguments to pass to the hook.
            **kwargs: Keyword arguments to pass to the hook.
        """
        for hooks in self._hooks:
            if not hasattr(hooks, hook_name):
                continue

            try:
                hook_method = getattr(hooks, hook_name)
                hook_method(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    "Hook execution failed",
                    extra={
                        "hook_name": hook_name,
                        "error": str(e),
                        "hook_type": type(hooks).__name__,
                    },
                    exc_info=True,
                )

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
