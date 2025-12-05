"""Container metrics and observability hooks.

**Feature: di-observability**
**Validates: Requirements for container monitoring and debugging**
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from core.di.lifecycle import Lifetime

logger = logging.getLogger(__name__)


@dataclass
class ContainerStats:
    """Statistics about container usage for observability.

    Tracks registration and resolution metrics to provide insight into
    container behavior and performance characteristics.
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
    """

    def on_service_registered(
        self, service_type: type, lifetime: Lifetime, factory: Any
    ) -> None:
        """Called when a service is registered."""
        ...

    def on_service_resolved(
        self, service_type: type, instance: Any, is_cached: bool
    ) -> None:
        """Called when a service is successfully resolved."""
        ...

    def on_resolution_error(
        self, service_type: type, error: Exception, resolution_stack: list[type]
    ) -> None:
        """Called when service resolution fails."""
        ...


class MetricsTracker:
    """Tracks container metrics and triggers hooks."""

    def __init__(self) -> None:
        self._metrics = ContainerStats()
        self._singleton_instances_created: set[type] = set()
        self._hooks: list[ContainerHooks] = []

    def record_registration(self, lifetime: Lifetime) -> None:
        """Record a service registration."""
        self._metrics.total_registrations += 1
        if lifetime == Lifetime.SINGLETON:
            self._metrics.singleton_registrations += 1
        elif lifetime == Lifetime.SCOPED:
            self._metrics.scoped_registrations += 1
        elif lifetime == Lifetime.TRANSIENT:
            self._metrics.transient_registrations += 1

    def record_resolution(self, service_type: type) -> None:
        """Record a service resolution attempt."""
        self._metrics.total_resolutions += 1
        type_name = service_type.__name__
        self._metrics.resolutions_by_type[type_name] = (
            self._metrics.resolutions_by_type.get(type_name, 0) + 1
        )

    def record_singleton_created(self, service_type: type) -> None:
        """Record singleton instance creation."""
        if service_type not in self._singleton_instances_created:
            self._singleton_instances_created.add(service_type)
            self._metrics.singleton_instances_created = len(
                self._singleton_instances_created
            )

    def get_stats(self) -> ContainerStats:
        """Get container usage statistics."""
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
        """Add observability hooks."""
        self._hooks.append(hooks)

    def trigger_hook(self, hook_name: str, **kwargs: Any) -> None:
        """Trigger all registered hooks for a specific event."""
        for hooks in self._hooks:
            if not hasattr(hooks, hook_name):
                continue

            try:
                hook_method = getattr(hooks, hook_name)
                hook_method(**kwargs)
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
