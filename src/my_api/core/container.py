"""Dependency injection container using dependency-injector.

**Feature: advanced-reusability**
**Validates: Requirements All**
"""

import logging
from collections.abc import Callable
from typing import Any

from dependency_injector import containers, providers

from my_api.core.config import Settings
from my_api.infrastructure.observability.telemetry import TelemetryProvider
from my_api.shared.caching import CacheConfig, InMemoryCacheProvider, RedisCacheProvider
from my_api.shared.cqrs import CommandBus, QueryBus

logger = logging.getLogger(__name__)


class Container(containers.DeclarativeContainer):
    """Application DI container.

    Manages all application dependencies including configuration,
    database sessions, repositories, mappers, use cases, caching,
    CQRS buses, and telemetry.
    """

    wiring_config = containers.WiringConfiguration(
        modules=[
            "my_api.adapters.api.routes.items",
            "my_api.adapters.api.routes.health",
        ]
    )

    # Configuration
    config = providers.Singleton(Settings)

    # Database session manager - configured at runtime via app.state.db
    db_session_manager = providers.Dependency()

    # Cache configuration
    cache_config = providers.Singleton(
        CacheConfig,
        ttl=3600,
        max_size=1000,
        key_prefix="myapi",
    )

    # In-memory cache provider
    memory_cache = providers.Singleton(
        InMemoryCacheProvider,
        config=cache_config,
    )

    # Redis cache provider (optional, configured at runtime)
    redis_cache = providers.Singleton(
        RedisCacheProvider,
        redis_url=providers.Callable(
            lambda cfg: cfg.database.url.replace("postgresql", "redis")
            if hasattr(cfg, "database")
            else "redis://localhost:6379",
            config,
        ),
        config=cache_config,
    )

    # CQRS Command Bus
    command_bus = providers.Singleton(CommandBus)

    # CQRS Query Bus with cache support
    query_bus = providers.Singleton(QueryBus)

    # Telemetry provider
    telemetry = providers.Singleton(
        TelemetryProvider,
        service_name=providers.Callable(
            lambda cfg: cfg.observability.service_name if hasattr(cfg, "observability") else "my-api",
            config,
        ),
        service_version=providers.Callable(
            lambda cfg: cfg.version if hasattr(cfg, "version") else "0.1.0",
            config,
        ),
        otlp_endpoint=providers.Callable(
            lambda cfg: cfg.observability.otlp_endpoint if hasattr(cfg, "observability") else None,
            config,
        ),
        enable_tracing=providers.Callable(
            lambda cfg: cfg.observability.enable_tracing if hasattr(cfg, "observability") else True,
            config,
        ),
        enable_metrics=providers.Callable(
            lambda cfg: cfg.observability.enable_metrics if hasattr(cfg, "observability") else True,
            config,
        ),
    )


class LifecycleManager:
    """Manages application lifecycle hooks for startup and shutdown.

    Provides a centralized way to register and execute startup/shutdown
    callbacks for resources like database connections, caches, etc.
    """

    def __init__(self) -> None:
        """Initialize lifecycle manager."""
        self._startup_hooks: list[Callable[[], Any]] = []
        self._shutdown_hooks: list[Callable[[], Any]] = []
        self._async_startup_hooks: list[Callable[[], Any]] = []
        self._async_shutdown_hooks: list[Callable[[], Any]] = []

    def on_startup(self, func: Callable[[], Any]) -> Callable[[], Any]:
        """Register a synchronous startup hook.

        Args:
            func: Function to call on startup.

        Returns:
            The registered function (for decorator use).
        """
        self._startup_hooks.append(func)
        return func

    def on_shutdown(self, func: Callable[[], Any]) -> Callable[[], Any]:
        """Register a synchronous shutdown hook.

        Args:
            func: Function to call on shutdown.

        Returns:
            The registered function (for decorator use).
        """
        self._shutdown_hooks.append(func)
        return func

    def on_startup_async(self, func: Callable[[], Any]) -> Callable[[], Any]:
        """Register an async startup hook.

        Args:
            func: Async function to call on startup.

        Returns:
            The registered function (for decorator use).
        """
        self._async_startup_hooks.append(func)
        return func

    def on_shutdown_async(self, func: Callable[[], Any]) -> Callable[[], Any]:
        """Register an async shutdown hook.

        Args:
            func: Async function to call on shutdown.

        Returns:
            The registered function (for decorator use).
        """
        self._async_shutdown_hooks.append(func)
        return func

    def run_startup(self) -> None:
        """Execute all synchronous startup hooks."""
        for hook in self._startup_hooks:
            try:
                logger.info(f"Running startup hook: {hook.__name__}")
                hook()
            except Exception as e:
                logger.error(f"Startup hook {hook.__name__} failed: {e}")
                raise

    def run_shutdown(self) -> None:
        """Execute all synchronous shutdown hooks in reverse order."""
        for hook in reversed(self._shutdown_hooks):
            try:
                logger.info(f"Running shutdown hook: {hook.__name__}")
                hook()
            except Exception as e:
                logger.error(f"Shutdown hook {hook.__name__} failed: {e}")

    async def run_startup_async(self) -> None:
        """Execute all async startup hooks."""
        for hook in self._async_startup_hooks:
            try:
                logger.info(f"Running async startup hook: {hook.__name__}")
                await hook()
            except Exception as e:
                logger.error(f"Async startup hook {hook.__name__} failed: {e}")
                raise

    async def run_shutdown_async(self) -> None:
        """Execute all async shutdown hooks in reverse order."""
        for hook in reversed(self._async_shutdown_hooks):
            try:
                logger.info(f"Running async shutdown hook: {hook.__name__}")
                await hook()
            except Exception as e:
                logger.error(f"Async shutdown hook {hook.__name__} failed: {e}")


# Global lifecycle manager instance
lifecycle = LifecycleManager()


def create_container(settings: Settings | None = None) -> Container:
    """Create and configure the DI container.

    Args:
        settings: Optional settings override.

    Returns:
        Container: Configured DI container.
    """
    container = Container()

    if settings:
        container.config.override(providers.Object(settings))

    return container
