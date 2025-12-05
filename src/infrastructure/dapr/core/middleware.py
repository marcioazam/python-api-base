"""Dapr middleware pipeline.

This module provides middleware support for Dapr request processing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from core.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MiddlewareRequest:
    """Request passing through middleware."""

    method: str
    path: str
    headers: dict[str, str]
    body: bytes | None
    metadata: dict[str, Any]


@dataclass
class MiddlewareResponse:
    """Response from middleware processing."""

    status_code: int
    headers: dict[str, str]
    body: bytes | None
    metadata: dict[str, Any]


class Middleware(ABC):
    """Base class for middleware components."""

    @abstractmethod
    async def process(
        self,
        request: MiddlewareRequest,
        next_handler: Callable[[MiddlewareRequest], Awaitable[MiddlewareResponse]],
    ) -> MiddlewareResponse:
        """Process the request.

        Args:
            request: Incoming request.
            next_handler: Next middleware or final handler.

        Returns:
            Response from processing.
        """
        ...


class LoggingMiddleware(Middleware):
    """Middleware that logs requests and responses."""

    async def process(
        self,
        request: MiddlewareRequest,
        next_handler: Callable[[MiddlewareRequest], Awaitable[MiddlewareResponse]],
    ) -> MiddlewareResponse:
        """Log request and response."""
        logger.info(
            "middleware_request",
            method=request.method,
            path=request.path,
        )

        response = await next_handler(request)

        logger.info(
            "middleware_response",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
        )

        return response


class TracingMiddleware(Middleware):
    """Middleware that adds tracing context."""

    async def process(
        self,
        request: MiddlewareRequest,
        next_handler: Callable[[MiddlewareRequest], Awaitable[MiddlewareResponse]],
    ) -> MiddlewareResponse:
        """Add tracing context to request."""
        try:
            from opentelemetry import trace
            from opentelemetry.trace.propagation.tracecontext import (
                TraceContextTextMapPropagator,
            )

            propagator = TraceContextTextMapPropagator()
            propagator.inject(request.headers)
        except ImportError:
            pass

        return await next_handler(request)


class ErrorHandlingMiddleware(Middleware):
    """Middleware that handles errors."""

    async def process(
        self,
        request: MiddlewareRequest,
        next_handler: Callable[[MiddlewareRequest], Awaitable[MiddlewareResponse]],
    ) -> MiddlewareResponse:
        """Handle errors in request processing."""
        try:
            return await next_handler(request)
        except Exception as e:
            logger.error(
                "middleware_error",
                method=request.method,
                path=request.path,
                error=str(e),
            )
            return MiddlewareResponse(
                status_code=500,
                headers={"Content-Type": "application/json"},
                body=b'{"error": "Internal server error"}',
                metadata={"error": str(e)},
            )


class MiddlewarePipeline:
    """Pipeline for chaining middleware components."""

    def __init__(self) -> None:
        """Initialize the middleware pipeline."""
        self._middlewares: list[Middleware] = []

    def add(self, middleware: Middleware) -> "MiddlewarePipeline":
        """Add middleware to the pipeline.

        Args:
            middleware: Middleware to add.

        Returns:
            Self for chaining.
        """
        self._middlewares.append(middleware)
        logger.debug("middleware_added", middleware=type(middleware).__name__)
        return self

    def remove(self, middleware_type: type[Middleware]) -> bool:
        """Remove middleware by type.

        Args:
            middleware_type: Type of middleware to remove.

        Returns:
            True if removed, False if not found.
        """
        for i, m in enumerate(self._middlewares):
            if isinstance(m, middleware_type):
                self._middlewares.pop(i)
                return True
        return False

    async def execute(
        self,
        request: MiddlewareRequest,
        final_handler: Callable[[MiddlewareRequest], Awaitable[MiddlewareResponse]],
    ) -> MiddlewareResponse:
        """Execute the middleware pipeline.

        Args:
            request: Incoming request.
            final_handler: Final handler after all middleware.

        Returns:
            Response from processing.
        """
        if not self._middlewares:
            return await final_handler(request)

        async def build_chain(
            index: int,
        ) -> Callable[[MiddlewareRequest], Awaitable[MiddlewareResponse]]:
            if index >= len(self._middlewares):
                return final_handler

            middleware = self._middlewares[index]

            async def next_handler(req: MiddlewareRequest) -> MiddlewareResponse:
                next_fn = await build_chain(index + 1)
                return await middleware.process(req, next_fn)

            return next_handler

        chain = await build_chain(0)
        return await chain(request)

    def get_middlewares(self) -> list[str]:
        """Get list of middleware names in order.

        Returns:
            List of middleware class names.
        """
        return [type(m).__name__ for m in self._middlewares]


def create_default_pipeline() -> MiddlewarePipeline:
    """Create a default middleware pipeline.

    Returns:
        MiddlewarePipeline with default middlewares.
    """
    pipeline = MiddlewarePipeline()
    pipeline.add(ErrorHandlingMiddleware())
    pipeline.add(LoggingMiddleware())
    pipeline.add(TracingMiddleware())
    return pipeline
