"""Health check endpoints for Kubernetes probes.

Provides /health/live, /health/ready, and /health/startup endpoints
for liveness, readiness, and startup probes.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    message: str | None = None
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Overall health check result."""

    status: HealthStatus
    timestamp: datetime
    components: list[ComponentHealth] = field(default_factory=list)
    version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                    "details": c.details,
                }
                for c in self.components
            ],
        }


# Health check registry
_health_checks: dict[str, Any] = {}
_startup_complete: bool = False
_app_version: str = "1.0.0"


def register_health_check(name: str, check_fn: Any) -> None:
    """Register a health check function.

    Args:
        name: Name of the component.
        check_fn: Async function that returns (is_healthy, message, details).
    """
    _health_checks[name] = check_fn


def set_startup_complete(complete: bool = True) -> None:
    """Mark startup as complete."""
    global _startup_complete
    _startup_complete = complete


def set_app_version(version: str) -> None:
    """Set application version for health responses."""
    global _app_version
    _app_version = version


async def _run_health_check(name: str, check_fn: Any) -> ComponentHealth:
    """Run a single health check with timing."""
    import time

    start = time.perf_counter()
    try:
        is_healthy, message, details = await check_fn()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name=name,
            status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
            message=message,
            latency_ms=round(latency, 2),
            details=details or {},
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        logger.error(f"Health check '{name}' failed: {e}")
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=str(e),
            latency_ms=round(latency, 2),
        )


async def _run_all_checks() -> HealthCheckResult:
    """Run all registered health checks."""
    if not _health_checks:
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            timestamp=datetime.now(tz=UTC),
            version=_app_version,
        )

    tasks = [_run_health_check(name, fn) for name, fn in _health_checks.items()]
    components = await asyncio.gather(*tasks)

    # Determine overall status
    if all(c.status == HealthStatus.HEALTHY for c in components):
        overall = HealthStatus.HEALTHY
    elif any(c.status == HealthStatus.UNHEALTHY for c in components):
        overall = HealthStatus.UNHEALTHY
    else:
        overall = HealthStatus.DEGRADED

    return HealthCheckResult(
        status=overall,
        timestamp=datetime.now(tz=UTC),
        components=list(components),
        version=_app_version,
    )


@router.get("/live")
async def liveness_probe(response: Response) -> dict[str, Any]:
    """Liveness probe endpoint.

    Returns 200 if the process is running. Used by Kubernetes
    to determine if the container should be restarted.

    This is a simple check - if the endpoint responds, the process is alive.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_probe(response: Response) -> dict[str, Any]:
    """Readiness probe endpoint.

    Returns 200 if the application is ready to receive traffic.
    Checks database, cache, and other dependencies.

    Used by Kubernetes to determine if traffic should be routed to this pod.
    """
    result = await _run_all_checks()

    if result.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result.to_dict()


@router.get("/startup")
async def startup_probe(response: Response) -> dict[str, Any]:
    """Startup probe endpoint.

    Returns 200 if the application has completed initialization.
    Used by Kubernetes to know when the application has started.

    Until this returns 200, liveness and readiness probes are disabled.
    """
    if not _startup_complete:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "starting",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "message": "Application is still initializing",
        }

    return {
        "status": "healthy",
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "message": "Application startup complete",
        "version": _app_version,
    }


@router.get("")
async def health_check(response: Response) -> dict[str, Any]:
    """Comprehensive health check endpoint.

    Returns detailed health status of all components.
    """
    result = await _run_all_checks()

    if result.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif result.status == HealthStatus.DEGRADED:
        response.status_code = status.HTTP_200_OK  # Still operational

    return result.to_dict()


# Example health check functions
async def check_database() -> tuple[bool, str | None, dict[str, Any] | None]:
    """Example database health check."""
    # In real implementation, check database connection
    return True, "Database connection OK", {"pool_size": 10, "active": 2}


async def check_cache() -> tuple[bool, str | None, dict[str, Any] | None]:
    """Example cache health check."""
    # In real implementation, ping cache server
    return True, "Cache connection OK", {"type": "redis"}
