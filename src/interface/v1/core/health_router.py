"""Health check routes with configurable timeout and metrics.

Provides Kubernetes-compatible health probes:
- /health/live - Liveness probe
- /health/ready - Readiness probe
- /health/startup - Startup probe

**Feature: advanced-reusability**
**Feature: enterprise-infrastructure-2025**
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
**Requirement: R6 - Kubernetes Health Checks**
"""

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from infrastructure.observability.telemetry import get_telemetry

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])

# Default timeout for health checks (seconds)
DEFAULT_HEALTH_CHECK_TIMEOUT = 5.0


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(BaseModel):
    """Health status for a single dependency."""

    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: HealthStatus
    checks: dict[str, DependencyHealth]
    version: str | None = None


# Metrics for health status tracking
_health_counter: Any = None
_health_latency: Any = None
_last_status: HealthStatus | None = None

# Startup state tracking
_startup_complete: bool = False
_startup_checks_passed: dict[str, bool] = {}


def _setup_metrics() -> None:
    """Initialize health check metrics."""
    global _health_counter, _health_latency
    meter = get_telemetry().get_meter()
    _health_counter = meter.create_counter(
        name="health_check_total",
        description="Total health check requests",
        unit="1",
    )
    _health_latency = meter.create_histogram(
        name="health_check_latency_seconds",
        description="Health check latency in seconds",
        unit="s",
    )


def _emit_status_change_metric(
    old_status: HealthStatus | None,
    new_status: HealthStatus,
) -> None:
    """Emit metric when health status changes.

    **Validates: Requirements 7.5**
    """
    global _last_status

    if old_status != new_status:
        logger.info(f"Health status changed: {old_status} -> {new_status}")
        if _health_counter:
            _health_counter.add(
                1,
                {"status": new_status.value, "changed": "true"},
            )
    elif _health_counter:
        _health_counter.add(
            1,
            {"status": new_status.value, "changed": "false"},
        )

    _last_status = new_status


async def _run_with_timeout(
    check_fn: Callable[..., Coroutine[Any, Any, DependencyHealth]],
    timeout: float,
    *args: Any,
    **kwargs: Any,
) -> DependencyHealth:
    """Run a health check with timeout.

    **Validates: Requirements 7.4**

    Args:
        check_fn: Async function to run.
        timeout: Timeout in seconds.
        *args: Positional arguments for check_fn.
        **kwargs: Keyword arguments for check_fn.

    Returns:
        DependencyHealth result or timeout failure.
    """
    try:
        return await asyncio.wait_for(
            check_fn(*args, **kwargs),
            timeout=timeout,
        )
    except TimeoutError:
        return DependencyHealth(
            status=HealthStatus.UNHEALTHY,
            message=f"Health check timed out after {timeout}s",
        )


async def check_database(request: Request) -> DependencyHealth:
    """Check database connectivity.

    Args:
        request: FastAPI request with app state.

    Returns:
        Database health status.
    """
    try:
        db = getattr(request.app.state, "db", None)
        if db is None:
            return DependencyHealth(
                status=HealthStatus.UNHEALTHY,
                message="Database not initialized",
            )

        start = time.perf_counter()
        async with db.session() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000

        return DependencyHealth(
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return DependencyHealth(
            status=HealthStatus.UNHEALTHY,
            message=str(e),
        )


async def check_redis(request: Request) -> DependencyHealth:
    """Check Redis connectivity (optional).

    Args:
        request: FastAPI request with app state.

    Returns:
        Redis health status.
    """
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return DependencyHealth(
                status=HealthStatus.HEALTHY,
                message="Redis not configured (optional)",
            )

        start = time.perf_counter()
        await redis.ping()
        latency = (time.perf_counter() - start) * 1000

        return DependencyHealth(
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return DependencyHealth(
            status=HealthStatus.DEGRADED,
            message=f"Redis unavailable: {e}",
        )


async def check_minio(request: Request) -> DependencyHealth:
    """Check MinIO connectivity (optional).

    **Requirement: R6.2 - Readiness with MinIO**

    Args:
        request: FastAPI request with app state.

    Returns:
        MinIO health status.
    """
    try:
        minio = getattr(request.app.state, "minio", None)
        if minio is None:
            return DependencyHealth(
                status=HealthStatus.HEALTHY,
                message="MinIO not configured (optional)",
            )

        start = time.perf_counter()
        # Try to list buckets as health check
        await asyncio.to_thread(minio.list_buckets)
        latency = (time.perf_counter() - start) * 1000

        return DependencyHealth(
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return DependencyHealth(
            status=HealthStatus.DEGRADED,
            message=f"MinIO unavailable: {e}",
        )


def mark_startup_complete() -> None:
    """Mark application startup as complete.

    Call this after all initialization is done.

    **Requirement: R6.3 - Startup probe**
    """
    global _startup_complete
    _startup_complete = True
    logger.info("Application startup complete")


def is_startup_complete() -> bool:
    """Check if startup is complete."""
    return _startup_complete


@router.get("/health/live", summary="Liveness check")
async def liveness() -> dict[str, str]:
    """Check if the service is alive.

    This endpoint is used by Kubernetes liveness probes.
    It should return 200 if the service is running.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 7.1, 24.1**
    """
    return {"status": "ok"}


@router.get(
    "/health/startup",
    summary="Startup check",
    responses={
        200: {"description": "Service has completed startup"},
        503: {"description": "Service is still starting up"},
    },
)
async def startup(response: Response) -> dict[str, str | bool]:
    """Check if the service has completed startup.

    This endpoint is used by Kubernetes startup probes.
    Returns 200 only after all dependencies are initialized.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 24.3**
    """
    if _startup_complete:
        return {"status": "ok", "startup_complete": True}
    response.status_code = 503
    return {"status": "starting", "startup_complete": False}


@router.get(
    "/health/ready",
    summary="Readiness check",
    response_model=HealthResponse,
)
async def readiness(
    request: Request,
    response: Response,
    timeout: float = Query(
        default=DEFAULT_HEALTH_CHECK_TIMEOUT,
        ge=0.1,
        le=30.0,
        description="Timeout for each health check in seconds",
    ),
) -> HealthResponse:
    """Check if the service is ready to accept requests.

    This endpoint checks all dependencies and returns detailed status.
    Used by Kubernetes readiness probes.

    **Validates: Requirements 7.2, 7.3, 7.4**
    """
    # Ensure metrics are set up
    if _health_counter is None:
        _setup_metrics()

    start_time = time.perf_counter()
    checks: dict[str, DependencyHealth] = {}

    # Check database with timeout
    checks["database"] = await _run_with_timeout(check_database, timeout, request)

    # Check Redis with timeout (optional)
    checks["redis"] = await _run_with_timeout(check_redis, timeout, request)

    # Check MinIO with timeout (optional)
    checks["minio"] = await _run_with_timeout(check_minio, timeout, request)

    # Determine overall status
    statuses = [check.status for check in checks.values()]

    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
        response.status_code = 503
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
        response.status_code = 200  # Still accepting requests
    else:
        overall_status = HealthStatus.HEALTHY

    # Emit metrics
    _emit_status_change_metric(_last_status, overall_status)

    # Record latency
    total_latency = time.perf_counter() - start_time
    if _health_latency:
        _health_latency.record(total_latency, {"status": overall_status.value})

    # Get version from settings
    settings = getattr(request.app.state, "settings", None)
    version = settings.version if settings else None

    return HealthResponse(
        status=overall_status,
        checks=checks,
        version=version,
    )
