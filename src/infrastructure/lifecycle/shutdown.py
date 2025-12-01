"""Graceful shutdown handling for FastAPI applications.

Handles SIGTERM/SIGINT signals to gracefully shutdown the application,
completing in-flight requests and cleaning up resources.
"""

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ShutdownState(Enum):
    """Application shutdown state."""

    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"


@dataclass
class ShutdownConfig:
    """Configuration for graceful shutdown."""

    timeout: float = 30.0  # Maximum time to wait for shutdown
    drain_timeout: float = 10.0  # Time to wait for in-flight requests
    force_exit: bool = True  # Force exit after timeout
    signals: list[signal.Signals] = field(
        default_factory=lambda: [signal.SIGTERM, signal.SIGINT]
    )


class ShutdownHandler:
    """Handler for graceful application shutdown.

    Manages shutdown hooks, signal handling, and resource cleanup.

    Example:
        >>> handler = ShutdownHandler()
        >>> handler.add_hook("database", close_database)
        >>> handler.add_hook("cache", close_cache)
        >>> 
        >>> # In FastAPI lifespan
        >>> @asynccontextmanager
        >>> async def lifespan(app):
        ...     handler.setup_signals()
        ...     yield
        ...     await handler.shutdown()
    """

    def __init__(self, config: ShutdownConfig | None = None) -> None:
        """Initialize shutdown handler.

        Args:
            config: Shutdown configuration.
        """
        self._config = config or ShutdownConfig()
        self._state = ShutdownState.RUNNING
        self._hooks: list[tuple[str, Callable[[], Awaitable[None]], int]] = []
        self._in_flight_requests = 0
        self._shutdown_event = asyncio.Event()
        self._started_at: datetime | None = None
        self._shutdown_at: datetime | None = None

    @property
    def state(self) -> ShutdownState:
        """Get current shutdown state."""
        return self._state

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._state != ShutdownState.RUNNING

    @property
    def in_flight_requests(self) -> int:
        """Get number of in-flight requests."""
        return self._in_flight_requests

    def add_hook(
        self,
        name: str,
        hook: Callable[[], Awaitable[None]],
        priority: int = 0,
    ) -> None:
        """Add a shutdown hook.

        Args:
            name: Name of the hook for logging.
            hook: Async function to call during shutdown.
            priority: Higher priority hooks run first.
        """
        self._hooks.append((name, hook, priority))
        # Sort by priority (higher first)
        self._hooks.sort(key=lambda x: x[2], reverse=True)
        logger.debug(f"Added shutdown hook: {name} (priority: {priority})")

    def remove_hook(self, name: str) -> bool:
        """Remove a shutdown hook by name.

        Args:
            name: Name of the hook to remove.

        Returns:
            True if removed, False if not found.
        """
        initial_len = len(self._hooks)
        self._hooks = [(n, h, p) for n, h, p in self._hooks if n != name]
        return len(self._hooks) < initial_len

    def setup_signals(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        for sig in self._config.signals:
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s)),
                )
                logger.info(f"Registered signal handler for {sig.name}")
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                logger.warning(
                    f"Signal handler for {sig.name} not supported on this platform"
                )

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signal.

        Args:
            sig: Signal received.
        """
        logger.info(f"Received signal {sig.name}, initiating graceful shutdown")
        await self.shutdown()

    def request_started(self) -> None:
        """Mark a request as started."""
        if self._state == ShutdownState.RUNNING:
            self._in_flight_requests += 1

    def request_finished(self) -> None:
        """Mark a request as finished."""
        self._in_flight_requests = max(0, self._in_flight_requests - 1)
        if self._state == ShutdownState.SHUTTING_DOWN and self._in_flight_requests == 0:
            self._shutdown_event.set()

    async def shutdown(self) -> None:
        """Perform graceful shutdown.

        Waits for in-flight requests to complete, then runs shutdown hooks.
        """
        if self._state != ShutdownState.RUNNING:
            logger.warning("Shutdown already in progress")
            return

        self._state = ShutdownState.SHUTTING_DOWN
        self._shutdown_at = datetime.now(tz=UTC)
        logger.info("Starting graceful shutdown")

        # Wait for in-flight requests to complete
        await self._drain_requests()

        # Run shutdown hooks
        await self._run_hooks()

        self._state = ShutdownState.SHUTDOWN
        logger.info("Graceful shutdown complete")

    async def _drain_requests(self) -> None:
        """Wait for in-flight requests to complete."""
        if self._in_flight_requests == 0:
            logger.info("No in-flight requests to drain")
            return

        logger.info(f"Waiting for {self._in_flight_requests} in-flight requests")

        try:
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=self._config.drain_timeout,
            )
            logger.info("All in-flight requests completed")
        except asyncio.TimeoutError:
            logger.warning(
                f"Drain timeout reached with {self._in_flight_requests} requests remaining"
            )

    async def _run_hooks(self) -> None:
        """Run all shutdown hooks."""
        for name, hook, priority in self._hooks:
            try:
                logger.info(f"Running shutdown hook: {name}")
                await asyncio.wait_for(
                    hook(),
                    timeout=self._config.timeout / len(self._hooks) if self._hooks else self._config.timeout,
                )
                logger.info(f"Shutdown hook completed: {name}")
            except asyncio.TimeoutError:
                logger.error(f"Shutdown hook timed out: {name}")
            except Exception as e:
                logger.error(f"Shutdown hook failed: {name} - {e}")

    def get_status(self) -> dict[str, Any]:
        """Get shutdown handler status."""
        return {
            "state": self._state.value,
            "in_flight_requests": self._in_flight_requests,
            "hooks_count": len(self._hooks),
            "hooks": [name for name, _, _ in self._hooks],
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "shutdown_at": self._shutdown_at.isoformat() if self._shutdown_at else None,
        }


class ShutdownMiddleware:
    """ASGI middleware for tracking in-flight requests.

    Integrates with ShutdownHandler to track requests and
    reject new requests during shutdown.
    """

    def __init__(
        self,
        app: Any,
        handler: ShutdownHandler,
        reject_during_shutdown: bool = True,
    ) -> None:
        """Initialize shutdown middleware.

        Args:
            app: ASGI application.
            handler: ShutdownHandler instance.
            reject_during_shutdown: Whether to reject new requests during shutdown.
        """
        self.app = app
        self.handler = handler
        self.reject_during_shutdown = reject_during_shutdown

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Process request with shutdown tracking."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Reject new requests during shutdown
        if self.reject_during_shutdown and self.handler.is_shutting_down:
            response = {
                "type": "http.response.start",
                "status": 503,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", b"30"),
                ],
            }
            await send(response)
            await send({
                "type": "http.response.body",
                "body": b'{"error": "Service is shutting down"}',
            })
            return

        # Track request
        self.handler.request_started()
        try:
            await self.app(scope, receive, send)
        finally:
            self.handler.request_finished()


@asynccontextmanager
async def graceful_shutdown_lifespan(
    app: Any,
    shutdown_handler: ShutdownHandler | None = None,
    startup_hooks: list[Callable[[], Awaitable[None]]] | None = None,
):
    """FastAPI lifespan context manager with graceful shutdown.

    Example:
        >>> handler = ShutdownHandler()
        >>> handler.add_hook("database", close_database)
        >>> 
        >>> app = FastAPI(lifespan=lambda app: graceful_shutdown_lifespan(app, handler))
    """
    handler = shutdown_handler or ShutdownHandler()
    handler._started_at = datetime.now(tz=UTC)

    # Setup signal handlers
    handler.setup_signals()

    # Run startup hooks
    if startup_hooks:
        for hook in startup_hooks:
            await hook()

    logger.info("Application started")

    try:
        yield
    finally:
        await handler.shutdown()


def create_shutdown_handler(
    timeout: float = 30.0,
    drain_timeout: float = 10.0,
) -> ShutdownHandler:
    """Factory function to create shutdown handler.

    Args:
        timeout: Maximum shutdown time.
        drain_timeout: Time to wait for in-flight requests.

    Returns:
        Configured ShutdownHandler.
    """
    config = ShutdownConfig(
        timeout=timeout,
        drain_timeout=drain_timeout,
    )
    return ShutdownHandler(config=config)
