"""Dependency Injection Container with PEP 695 type parameters.

This module has been refactored into smaller, focused modules:
- di/resolution/: DI-specific exceptions and resolver
- di/lifecycle/: Lifetime enum and Registration dataclass
- di/observability/: ContainerStats, ContainerHooks, MetricsTracker
- di/container/: Container and Scope classes

This file now contains the main Container class only.

**Feature: generics-100-percent-fixes**
**Validates: Requirements 28.1, 28.2, 28.3, 4.1, 4.2, 4.3, 4.4, 4.5**
**Refactored: 2025 - Split into focused modules, uses MetricsTracker**
"""

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from core.di.resolution import CircularDependencyError, ServiceNotRegisteredError, Resolver
from core.di.lifecycle import Lifetime, Registration
from core.di.observability import ContainerHooks, ContainerStats, MetricsTracker
from core.di.container.scopes import Scope

# Re-export for backward compatibility
__all__ = [
    "Container",
    "ContainerHooks",
    "ContainerStats",
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
        """Initialize container with metrics tracking and observability hooks."""
        self._registrations: dict[type, Registration[Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._resolution_stack: list[type] = []
        self._resolver = Resolver(self._registrations, self.resolve)
        self._metrics_tracker = MetricsTracker()

    def register[T](
        self,
        service_type: type[T],
        factory: Callable[..., T] | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> None:
        """Register a service with the container.

        Args:
            service_type: The type to register.
            factory: Factory function to create instances. If None, uses service_type.
            lifetime: Lifetime of the service (TRANSIENT, SINGLETON, SCOPED).

        Raises:
            InvalidFactoryError: If factory is not callable or has invalid signature.
        """
        if factory is None:
            factory = service_type

        self._resolver.validate_factory(factory, service_type)

        self._registrations[service_type] = Registration(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime,
        )

        self._metrics_tracker.record_registration(lifetime)
        self._metrics_tracker.trigger_hook(
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
        """Register a singleton service."""
        self.register(service_type, factory, Lifetime.SINGLETON)

    def register_scoped[T](
        self,
        service_type: type[T],
        factory: Callable[..., T] | None = None,
    ) -> None:
        """Register a scoped service."""
        self.register(service_type, factory, Lifetime.SCOPED)

    def register_instance[T](
        self,
        service_type: type[T],
        instance: T,
    ) -> None:
        """Register an existing instance as singleton."""
        self._registrations[service_type] = Registration(
            service_type=service_type,
            factory=lambda: instance,
            lifetime=Lifetime.SINGLETON,
            instance=instance,
        )
        self._singletons[service_type] = instance

        self._metrics_tracker.record_registration(Lifetime.SINGLETON)
        self._metrics_tracker.record_singleton_created(service_type)

    def resolve[T](self, service_type: type[T]) -> T:
        """Resolve a service from the container.

        Args:
            service_type: The type to resolve.

        Returns:
            Instance of the requested type.

        Raises:
            ServiceNotRegisteredError: If service is not registered.
            CircularDependencyError: If circular dependency detected.
            DependencyResolutionError: If dependency cannot be resolved.
        """
        try:
            if service_type not in self._registrations:
                raise ServiceNotRegisteredError(service_type)

            if service_type in self._resolution_stack:
                chain = [*self._resolution_stack, service_type]
                raise CircularDependencyError(chain)
        except Exception as e:
            self._metrics_tracker.trigger_hook(
                "on_resolution_error",
                service_type=service_type,
                error=e,
                resolution_stack=self._resolution_stack.copy(),
            )
            raise

        registration = self._registrations[service_type]
        self._metrics_tracker.record_resolution(service_type)

        if registration.lifetime == Lifetime.SINGLETON:
            return self._resolve_singleton(service_type, registration)

        return self._resolve_transient(service_type, registration)

    def _resolve_singleton[T](
        self, service_type: type[T], registration: Registration[T]
    ) -> T:
        """Resolve singleton service."""
        if service_type in self._singletons:
            instance = self._singletons[service_type]
            self._metrics_tracker.trigger_hook(
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
            self._metrics_tracker.trigger_hook(
                "on_resolution_error",
                service_type=service_type,
                error=e,
                resolution_stack=self._resolution_stack.copy(),
            )
            raise
        finally:
            self._resolution_stack.pop()

        self._singletons[service_type] = instance
        self._metrics_tracker.record_singleton_created(service_type)
        self._metrics_tracker.trigger_hook(
            "on_service_resolved",
            service_type=service_type,
            instance=instance,
            is_cached=False,
        )

        return instance

    def _resolve_transient[T](
        self, service_type: type[T], registration: Registration[T]
    ) -> T:
        """Resolve transient/scoped service."""
        self._resolution_stack.append(service_type)
        try:
            instance = self._resolver.create_instance(registration)
            self._metrics_tracker.trigger_hook(
                "on_service_resolved",
                service_type=service_type,
                instance=instance,
                is_cached=False,
            )
            return instance
        except Exception as e:
            self._metrics_tracker.trigger_hook(
                "on_resolution_error",
                service_type=service_type,
                error=e,
                resolution_stack=self._resolution_stack.copy(),
            )
            raise
        finally:
            self._resolution_stack.pop()

    def is_registered(self, service_type: type) -> bool:
        """Check if a service is registered."""
        return service_type in self._registrations

    def get_registration[T](self, service_type: type[T]) -> Registration[T]:
        """Get registration for a service type.

        Args:
            service_type: The type to get registration for.

        Returns:
            Registration entry for the service.

        Raises:
            ServiceNotRegisteredError: If service is not registered.
        """
        if service_type not in self._registrations:
            raise ServiceNotRegisteredError(service_type)
        return self._registrations[service_type]

    def create_instance[T](self, registration: Registration[T]) -> T:
        """Create an instance using the factory with auto-wiring.

        Args:
            registration: The registration entry for the service.

        Returns:
            Created instance of type T.
        """
        return self._resolver.create_instance(registration)

    def get_stats(self) -> ContainerStats:
        """Get container usage statistics for observability."""
        return self._metrics_tracker.get_stats()

    def add_hooks(self, hooks: ContainerHooks) -> None:
        """Add observability hooks to the container."""
        self._metrics_tracker.add_hooks(hooks)

    def clear_singletons(self) -> None:
        """Clear all singleton instances.

        Useful for testing to ensure clean state between tests.
        Does not remove registrations, only cached instances.
        """
        self._singletons.clear()
        self._metrics_tracker.trigger_hook(
            "on_singletons_cleared",
            count=len(self._singletons),
        )

    @contextmanager
    def create_scope(self):
        """Create a new scope for scoped dependencies.

        Yields:
            Scope: A new scope instance.
        """
        scope = Scope(self)
        try:
            yield scope
        finally:
            scope.dispose()
