"""Dependency lifecycle and registration types.

**Feature: generics-100-percent-fixes**
**Validates: Requirements 28.1, 28.2, 28.3**
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class Lifetime(Enum):
    """Dependency lifetime options.

    Controls how instances are created and cached by the container.

    **Feature: generics-100-percent-fixes**
    **Validates: Requirements 28.1, 28.2, 28.3**
    """

    TRANSIENT = "transient"  # New instance every time
    SINGLETON = "singleton"  # Same instance always (cached globally)
    SCOPED = "scoped"  # Same instance within scope (cached per scope)


@dataclass
class Registration[T]:
    """Registration entry for a dependency.

    Stores the factory function, lifetime, and cached instance (if applicable).

    Type Parameters:
        T: The type being registered.

    **Feature: generics-100-percent-fixes**
    **Validates: Requirements 28.1**
    """

    service_type: type[T]
    factory: Callable[..., T]
    lifetime: Lifetime = Lifetime.TRANSIENT
    instance: T | None = None
