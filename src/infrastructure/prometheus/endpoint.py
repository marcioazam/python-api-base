"""Prometheus metrics endpoint for FastAPI.

**Feature: observability-infrastructure**
**Requirement: R5 - Prometheus Metrics**
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Response

from infrastructure.prometheus.registry import MetricsRegistry, get_registry

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_metrics_endpoint(
    registry: MetricsRegistry | None = None,
    path: str = "/metrics",
    include_in_schema: bool = False,
    tags: list[str] | None = None,
) -> APIRouter:
    """Create a FastAPI router for Prometheus metrics endpoint.

    **Feature: observability-infrastructure**
    **Requirement: R5.4 - Metrics Endpoint**

    Args:
        registry: Metrics registry (uses global if not provided)
        path: Endpoint path
        include_in_schema: Include in OpenAPI schema
        tags: OpenAPI tags

    Returns:
        FastAPI APIRouter with metrics endpoint

    Example:
        >>> app.include_router(create_metrics_endpoint())
    """
    router = APIRouter(tags=tags or ["Metrics"])
    metrics_registry = registry or get_registry()

    @router.get(
        path,
        include_in_schema=include_in_schema,
        response_class=Response,
        summary="Prometheus Metrics",
        description="Returns metrics in Prometheus text format",
    )
    async def metrics() -> Response:
        """Return Prometheus metrics."""
        return Response(
            content=metrics_registry.generate_metrics(),
            media_type=metrics_registry.content_type(),
        )

    return router


def setup_prometheus(
    app: "FastAPI",
    registry: MetricsRegistry | None = None,
    endpoint: str = "/metrics",
    include_in_schema: bool = False,
    skip_paths: list[str] | None = None,
) -> None:
    """Setup Prometheus metrics for a FastAPI application.

    Adds middleware and metrics endpoint.

    **Feature: observability-infrastructure**
    **Requirement: R5.5 - FastAPI Integration**

    Args:
        app: FastAPI application
        registry: Metrics registry
        endpoint: Metrics endpoint path
        include_in_schema: Include endpoint in OpenAPI schema
        skip_paths: Paths to skip from metrics collection

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> setup_prometheus(app)
    """
    from infrastructure.prometheus.middleware import PrometheusMiddleware

    # Add middleware
    app.add_middleware(
        PrometheusMiddleware,
        registry=registry,
        skip_paths=skip_paths,
    )

    # Add endpoint
    router = create_metrics_endpoint(
        registry=registry,
        path=endpoint,
        include_in_schema=include_in_schema,
    )
    app.include_router(router)
