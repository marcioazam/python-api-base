"""Scoped dependency management.

**Feature: generics-100-percent-fixes**
**Validates: Requirements 28.3**
"""

from typing import TYPE_CHECKING, Any

from .exceptions import CircularDependencyError, ServiceNotRegisteredError
from .lifecycle import Lifetime

if TYPE_CHECKING:
    from .container import Container


class Scope:
    """Scoped container for scoped dependencies.

    Maintains separate instances for SCOPED lifetime services within a scope.
    Delegates to parent container for SINGLETON and TRANSIENT services.

    **Feature: generics-100-percent-fixes**
    **Validates: Requirements 28.3**
    """

    def __init__(self, parent: "Container") -> None:
        """Initialize scope.

        Args:
            parent: The parent container to delegate to.
        """
        self._parent = parent
        self._scoped_instances: dict[type, Any] = {}
        self._resolution_stack: list[type] = []

    def resolve[T](self, service_type: type[T]) -> T:
        """Resolve a service within this scope.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 28.3**

        Args:
            service_type: The type to resolve.

        Returns:
            Instance of the requested type.

        Raises:
            ServiceNotRegisteredError: If service is not registered.
            CircularDependencyError: If circular dependency detected.
        """
        if service_type not in self._parent._registrations:
            raise ServiceNotRegisteredError(service_type)

        # Check for circular dependency
        if service_type in self._resolution_stack:
            chain = self._resolution_stack + [service_type]
            raise CircularDependencyError(chain)

        registration = self._parent._registrations[service_type]

        if registration.lifetime == Lifetime.SINGLETON:
            return self._parent.resolve(service_type)

        if registration.lifetime == Lifetime.SCOPED:
            if service_type in self._scoped_instances:
                return self._scoped_instances[service_type]

            self._resolution_stack.append(service_type)
            try:
                instance = self._parent._resolver.create_instance(registration)
            finally:
                self._resolution_stack.pop()

            self._scoped_instances[service_type] = instance
            return instance

        self._resolution_stack.append(service_type)
        try:
            return self._parent._resolver.create_instance(registration)
        finally:
            self._resolution_stack.pop()

    def dispose(self) -> None:
        """Dispose of scoped instances.

        Calls dispose() or close() methods on scoped instances if available.
        """
        for instance in self._scoped_instances.values():
            if hasattr(instance, "dispose"):
                instance.dispose()
            elif hasattr(instance, "close"):
                instance.close()
        self._scoped_instances.clear()
