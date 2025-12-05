"""Dependency Injection exceptions.

**Feature: generics-100-percent-fixes**
**Validates: Requirements 4.1, 4.2, 4.4, 4.5**
"""

from collections.abc import Callable
from typing import Any


class DependencyResolutionError(Exception):
    """Raised when dependency cannot be resolved.

    **Feature: generics-100-percent-fixes**
    **Validates: Requirements 4.1, 4.4**
    """

    def __init__(
        self,
        service_type: type,
        param_name: str,
        expected_type: type,
        reason: str | None = None,
    ) -> None:
        """Initialize dependency resolution error.

        Args:
            service_type: The service type that failed to resolve.
            param_name: The parameter name that failed.
            expected_type: The expected type for the parameter.
            reason: Optional reason for failure.
        """
        self.service_type = service_type
        self.param_name = param_name
        self.expected_type = expected_type
        self.reason = reason

        msg = (
            f"Cannot resolve parameter '{param_name}' of type "
            f"'{expected_type.__name__}' for service '{service_type.__name__}'"
        )
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class CircularDependencyError(Exception):
    """Raised when circular dependency is detected.

    **Feature: generics-100-percent-fixes**
    **Validates: Requirements 4.2**
    """

    def __init__(self, chain: list[type]) -> None:
        """Initialize circular dependency error.

        Args:
            chain: The chain of types forming the circular dependency.
        """
        self.chain = chain
        chain_str = " -> ".join(t.__name__ for t in chain)
        super().__init__(f"Circular dependency detected: {chain_str}")


class InvalidFactoryError(Exception):
    """Raised when factory signature is invalid.

    **Feature: generics-100-percent-fixes**
    **Validates: Requirements 4.5**
    """

    def __init__(self, factory: Callable[..., Any], reason: str) -> None:
        """Initialize invalid factory error.

        Args:
            factory: The invalid factory function or class.
            reason: Reason why the factory is invalid.
        """
        self.factory = factory
        self.reason = reason
        factory_name = getattr(factory, "__name__", str(factory))
        super().__init__(f"Invalid factory '{factory_name}': {reason}")


class ServiceNotRegisteredError(Exception):
    """Raised when service is not registered in container."""

    def __init__(self, service_type: type) -> None:
        """Initialize service not registered error.

        Args:
            service_type: The service type that was not found.
        """
        self.service_type = service_type
        super().__init__(f"Service '{service_type.__name__}' is not registered")
