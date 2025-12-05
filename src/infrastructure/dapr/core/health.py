"""Dapr health checks.

This module provides health check capabilities for Dapr sidecar and components.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum

import httpx

from core.shared.logging import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a Dapr component."""

    name: str
    type: str
    status: HealthStatus
    message: str | None = None


@dataclass
class DaprHealth:
    """Overall Dapr health status."""

    sidecar_status: HealthStatus
    components: list[ComponentHealth]
    version: str | None = None


class HealthChecker:
    """Checks Dapr sidecar and component health."""

    def __init__(self, dapr_http_endpoint: str = "http://localhost:3500") -> None:
        """Initialize the health checker.

        Args:
            dapr_http_endpoint: Dapr HTTP endpoint.
        """
        self._endpoint = dapr_http_endpoint

    async def check_sidecar_health(self) -> HealthStatus:
        """Check Dapr sidecar health via /healthz endpoint.

        Returns:
            HealthStatus indicating sidecar health.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._endpoint}/v1.0/healthz",
                    timeout=5.0,
                )
                if response.status_code == 204:
                    return HealthStatus.HEALTHY
                return HealthStatus.DEGRADED
        except httpx.RequestError:
            return HealthStatus.UNHEALTHY

    async def check_outbound_health(self) -> HealthStatus:
        """Check Dapr outbound health.

        Returns:
            HealthStatus indicating outbound health.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._endpoint}/v1.0/healthz/outbound",
                    timeout=5.0,
                )
                if response.status_code == 204:
                    return HealthStatus.HEALTHY
                return HealthStatus.DEGRADED
        except httpx.RequestError:
            return HealthStatus.UNHEALTHY

    async def check_component_health(
        self,
        component_name: str,
        component_type: str = "unknown",
    ) -> ComponentHealth:
        """Check health of a specific component.

        Args:
            component_name: Component name.
            component_type: Component type (e.g., "state", "pubsub").

        Returns:
            ComponentHealth with status.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._endpoint}/v1.0/metadata",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    metadata = response.json()
                    components = metadata.get("components", [])

                    for comp in components:
                        if comp.get("name") == component_name:
                            return ComponentHealth(
                                name=component_name,
                                type=comp.get("type", component_type),
                                status=HealthStatus.HEALTHY,
                            )

                    return ComponentHealth(
                        name=component_name,
                        type=component_type,
                        status=HealthStatus.UNHEALTHY,
                        message="Component not found",
                    )

                return ComponentHealth(
                    name=component_name,
                    type=component_type,
                    status=HealthStatus.DEGRADED,
                    message=f"Metadata request failed: {response.status_code}",
                )
        except httpx.RequestError as e:
            return ComponentHealth(
                name=component_name,
                type=component_type,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )

    async def get_full_health(self) -> DaprHealth:
        """Get full health status including all components.

        Returns:
            DaprHealth with sidecar and component status.
        """
        sidecar_status = await self.check_sidecar_health()
        components: list[ComponentHealth] = []
        version: str | None = None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._endpoint}/v1.0/metadata",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    metadata = response.json()
                    version = metadata.get("runtimeVersion")

                    for comp in metadata.get("components", []):
                        components.append(
                            ComponentHealth(
                                name=comp.get("name", "unknown"),
                                type=comp.get("type", "unknown"),
                                status=HealthStatus.HEALTHY,
                            )
                        )
        except httpx.RequestError:
            pass

        return DaprHealth(
            sidecar_status=sidecar_status,
            components=components,
            version=version,
        )

    async def wait_for_sidecar(
        self,
        timeout_seconds: int = 60,
        poll_interval_seconds: float = 0.5,
    ) -> bool:
        """Wait for Dapr sidecar to be ready.

        Args:
            timeout_seconds: Maximum time to wait.
            poll_interval_seconds: Interval between health checks.

        Returns:
            True if sidecar is ready, False if timeout.
        """
        elapsed = 0.0

        logger.info(
            "waiting_for_dapr_sidecar",
            endpoint=self._endpoint,
            timeout=timeout_seconds,
        )

        while elapsed < timeout_seconds:
            status = await self.check_sidecar_health()
            if status == HealthStatus.HEALTHY:
                logger.info("dapr_sidecar_ready", elapsed=elapsed)
                return True

            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds

        logger.error(
            "dapr_sidecar_timeout",
            timeout=timeout_seconds,
        )
        return False

    async def is_ready(self) -> bool:
        """Check if Dapr is ready to accept requests.

        Returns:
            True if ready, False otherwise.
        """
        status = await self.check_sidecar_health()
        return status == HealthStatus.HEALTHY
