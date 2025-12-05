"""Dependency Injection module.

Organized into subpackages by responsibility:
- container/: Container and Scope classes
- resolution/: Resolver and exceptions
- lifecycle/: Lifetime and Registration
- observability/: Metrics tracking

This module provides a type-safe dependency injection container with:
- Auto-wiring of constructor dependencies
- Lifetime management (TRANSIENT, SINGLETON, SCOPED)
- Circular dependency detection
- PEP 695 generics support

**Feature: generics-100-percent-fixes**
**Validates: Requirements 28.1, 28.2, 28.3, 4.1, 4.2, 4.3, 4.4, 4.5**

Example:
    >>> from core.di import Container, Lifetime
    >>> container = Container()
    >>> container.register(Database, lifetime=Lifetime.SINGLETON)
    >>> container.register(UserService)
    >>> service = container.resolve(UserService)
"""

from core.di.container import Container, Scope
from core.di.resolution import (
    CircularDependencyError,
    DependencyResolutionError,
    InvalidFactoryError,
    ServiceNotRegisteredError,
)
from core.di.lifecycle import Lifetime, Registration
from core.di.observability import ContainerHooks, ContainerStats, MetricsTracker

__all__ = [
    "CircularDependencyError",
    # Container
    "Container",
    "ContainerHooks",
    # Metrics
    "ContainerStats",
    # Exceptions
    "DependencyResolutionError",
    "InvalidFactoryError",
    # Lifecycle
    "Lifetime",
    "MetricsTracker",
    "Registration",
    "Scope",
    "ServiceNotRegisteredError",
]
