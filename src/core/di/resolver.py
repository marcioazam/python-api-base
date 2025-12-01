"""Dependency resolution logic.

**Feature: generics-100-percent-fixes**
**Validates: Requirements 4.1, 4.3, 4.4, 4.5**
"""

import inspect
import types
from collections.abc import Callable
from typing import Any, Union, get_args, get_origin, get_type_hints

from .exceptions import DependencyResolutionError, InvalidFactoryError
from .lifecycle import Registration


class Resolver:
    """Handles dependency resolution with auto-wiring.

    **Feature: generics-100-percent-fixes**
    **Validates: Requirements 4.1, 4.3, 4.4**
    """

    def __init__(
        self,
        registrations: dict[type, Registration[Any]],
        resolve_callback: Callable[[type], Any],
    ) -> None:
        """Initialize resolver.

        Args:
            registrations: Dictionary of registered services.
            resolve_callback: Callback to resolve dependencies (typically Container.resolve).
        """
        self._registrations = registrations
        self._resolve = resolve_callback

    def validate_factory(
        self,
        factory: Callable[..., Any],
        service_type: type,
    ) -> None:
        """Validate factory is callable and has valid signature.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 4.5**

        Args:
            factory: Factory function or class to validate.
            service_type: The service type being registered.

        Raises:
            InvalidFactoryError: If factory is invalid.
        """
        if not callable(factory):
            raise InvalidFactoryError(factory, "Factory must be callable")

        # Check if it's a class or function
        if inspect.isclass(factory):
            # For classes, check __init__
            try:
                inspect.signature(factory.__init__)
            except (ValueError, TypeError) as e:
                raise InvalidFactoryError(factory, f"Cannot inspect __init__: {e}")
        else:
            try:
                inspect.signature(factory)
            except (ValueError, TypeError) as e:
                raise InvalidFactoryError(factory, f"Cannot inspect signature: {e}")

    def create_instance[T](self, registration: Registration[T]) -> T:
        """Create an instance using the factory with auto-wiring.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 4.1, 4.3**

        Args:
            registration: The registration entry for the service.

        Returns:
            Created instance of type T.

        Raises:
            DependencyResolutionError: If dependency cannot be resolved.
        """
        factory = registration.factory
        service_type = registration.service_type

        # Get type hints for auto-wiring
        try:
            if inspect.isclass(factory):
                hints = get_type_hints(factory.__init__)
            else:
                hints = get_type_hints(factory)
        except Exception as e:
            # If we can't get hints, try to call without args
            try:
                return factory()
            except TypeError:
                raise DependencyResolutionError(
                    service_type=service_type,
                    param_name="<unknown>",
                    expected_type=type(None),
                    reason=f"Cannot get type hints: {e}",
                )

        # Remove 'return' from hints
        hints.pop("return", None)

        # Resolve dependencies
        kwargs: dict[str, Any] = {}
        for param_name, param_type in hints.items():
            resolved = self._resolve_parameter(
                service_type=service_type,
                param_name=param_name,
                param_type=param_type,
            )
            if resolved is not None or self._is_optional(param_type):
                kwargs[param_name] = resolved

        try:
            return factory(**kwargs)
        except TypeError as e:
            raise DependencyResolutionError(
                service_type=service_type,
                param_name="<constructor>",
                expected_type=service_type,
                reason=f"Factory call failed: {e}",
            )

    def _resolve_parameter(
        self,
        service_type: type,
        param_name: str,
        param_type: type,
    ) -> Any:
        """Resolve a single parameter.

        **Feature: generics-100-percent-fixes**
        **Validates: Requirements 4.1, 4.4**

        Args:
            service_type: The service type being created.
            param_name: The parameter name to resolve.
            param_type: The parameter type to resolve.

        Returns:
            Resolved value or None for optional parameters.

        Raises:
            DependencyResolutionError: If required parameter cannot be resolved.
        """
        # Handle Optional[T] / T | None
        actual_type = self._unwrap_optional(param_type)
        is_optional = self._is_optional(param_type)

        if actual_type in self._registrations:
            return self._resolve(actual_type)

        if is_optional:
            return None

        raise DependencyResolutionError(
            service_type=service_type,
            param_name=param_name,
            expected_type=actual_type,
            reason="Service not registered",
        )

    def _is_optional(self, param_type: type) -> bool:
        """Check if type is Optional[T] or T | None.

        Args:
            param_type: The type to check.

        Returns:
            True if type is optional, False otherwise.
        """
        origin = get_origin(param_type)

        # Handle Union types (Optional[T] is Union[T, None])
        if origin is Union:
            args = get_args(param_type)
            return type(None) in args

        # Handle Python 3.10+ T | None syntax
        if origin is types.UnionType:
            args = get_args(param_type)
            return type(None) in args

        return False

    def _unwrap_optional(self, param_type: type) -> type:
        """Unwrap Optional[T] to get T.

        Args:
            param_type: The type to unwrap.

        Returns:
            The unwrapped type (T from Optional[T]).
        """
        origin = get_origin(param_type)

        if origin is Union or origin is types.UnionType:
            args = get_args(param_type)
            # Return first non-None type
            for arg in args:
                if arg is not type(None):
                    return arg

        return param_type
