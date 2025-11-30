"""Smart Routing Pattern Implementation.

This module provides smart routing with load balancing and
routing based on metrics.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.4**
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"


class EndpointStatus(Enum):
    """Status of an endpoint."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class EndpointMetrics:
    """Metrics for an endpoint."""

    request_count: int = 0
    error_count: int = 0
    total_response_time_ms: float = 0.0
    active_connections: int = 0
    last_check: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_error: datetime | None = None

    @property
    def avg_response_time_ms(self) -> float:
        """Calculate average response time."""
        if self.request_count == 0:
            return 0.0
        return self.total_response_time_ms / self.request_count

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count

    def record_request(self, response_time_ms: float, is_error: bool = False) -> None:
        """Record a request."""
        self.request_count += 1
        self.total_response_time_ms += response_time_ms
        if is_error:
            self.error_count += 1
            self.last_error = datetime.now(UTC)

    def increment_connections(self) -> None:
        """Increment active connections."""
        self.active_connections += 1

    def decrement_connections(self) -> None:
        """Decrement active connections."""
        self.active_connections = max(0, self.active_connections - 1)


@dataclass
class Endpoint:
    """Represents a routable endpoint."""

    id: str
    url: str
    weight: int = 1
    status: EndpointStatus = EndpointStatus.UNKNOWN
    metrics: EndpointMetrics = field(default_factory=EndpointMetrics)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        """Check if endpoint is available for routing."""
        return self.status in (EndpointStatus.HEALTHY, EndpointStatus.UNKNOWN)


class LoadBalancer(ABC):
    """Abstract base class for load balancers."""

    @abstractmethod
    def select(self, endpoints: list[Endpoint], context: dict[str, Any]) -> Endpoint | None:
        """Select an endpoint from the list."""
        ...


class RoundRobinBalancer(LoadBalancer):
    """Round-robin load balancer."""

    def __init__(self) -> None:
        self._index = 0

    def select(self, endpoints: list[Endpoint], context: dict[str, Any]) -> Endpoint | None:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None

        endpoint = available[self._index % len(available)]
        self._index += 1
        return endpoint


class RandomBalancer(LoadBalancer):
    """Random load balancer."""

    def select(self, endpoints: list[Endpoint], context: dict[str, Any]) -> Endpoint | None:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        return random.choice(available)


class LeastConnectionsBalancer(LoadBalancer):
    """Least connections load balancer."""

    def select(self, endpoints: list[Endpoint], context: dict[str, Any]) -> Endpoint | None:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        return min(available, key=lambda e: e.metrics.active_connections)


class WeightedBalancer(LoadBalancer):
    """Weighted load balancer."""

    def select(self, endpoints: list[Endpoint], context: dict[str, Any]) -> Endpoint | None:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None

        total_weight = sum(e.weight for e in available)
        if total_weight == 0:
            return random.choice(available)

        r = random.uniform(0, total_weight)
        cumulative = 0
        for endpoint in available:
            cumulative += endpoint.weight
            if r <= cumulative:
                return endpoint

        return available[-1]


class LeastResponseTimeBalancer(LoadBalancer):
    """Least response time load balancer."""

    def select(self, endpoints: list[Endpoint], context: dict[str, Any]) -> Endpoint | None:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None
        return min(available, key=lambda e: e.metrics.avg_response_time_ms)


class IPHashBalancer(LoadBalancer):
    """IP hash load balancer for session affinity."""

    def select(self, endpoints: list[Endpoint], context: dict[str, Any]) -> Endpoint | None:
        available = [e for e in endpoints if e.is_available]
        if not available:
            return None

        client_ip = context.get("client_ip", "")
        if not client_ip:
            return random.choice(available)

        hash_value = hash(client_ip)
        index = hash_value % len(available)
        return available[index]



class SmartRouter[T]:
    """Smart router with load balancing and health checking."""

    def __init__(
        self,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        health_check_interval: timedelta = timedelta(seconds=30),
        error_threshold: float = 0.5,
    ) -> None:
        self._strategy = strategy
        self._balancer = self._create_balancer(strategy)
        self._endpoints: dict[str, Endpoint] = {}
        self._health_check_interval = health_check_interval
        self._error_threshold = error_threshold

    def _create_balancer(self, strategy: LoadBalancingStrategy) -> LoadBalancer:
        """Create a load balancer for the strategy."""
        balancers = {
            LoadBalancingStrategy.ROUND_ROBIN: RoundRobinBalancer,
            LoadBalancingStrategy.RANDOM: RandomBalancer,
            LoadBalancingStrategy.LEAST_CONNECTIONS: LeastConnectionsBalancer,
            LoadBalancingStrategy.WEIGHTED: WeightedBalancer,
            LoadBalancingStrategy.LEAST_RESPONSE_TIME: LeastResponseTimeBalancer,
            LoadBalancingStrategy.IP_HASH: IPHashBalancer,
        }
        return balancers[strategy]()

    def add_endpoint(
        self,
        endpoint_id: str,
        url: str,
        weight: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> "SmartRouter[T]":
        """Add an endpoint to the router."""
        self._endpoints[endpoint_id] = Endpoint(
            id=endpoint_id,
            url=url,
            weight=weight,
            status=EndpointStatus.UNKNOWN,
            metadata=metadata or {},
        )
        return self

    def remove_endpoint(self, endpoint_id: str) -> bool:
        """Remove an endpoint from the router."""
        return self._endpoints.pop(endpoint_id, None) is not None

    def get_endpoint(self, endpoint_id: str) -> Endpoint | None:
        """Get an endpoint by ID."""
        return self._endpoints.get(endpoint_id)

    def select_endpoint(self, context: dict[str, Any] | None = None) -> Endpoint | None:
        """Select an endpoint using the load balancing strategy."""
        endpoints = list(self._endpoints.values())
        return self._balancer.select(endpoints, context or {})

    def record_request(
        self,
        endpoint_id: str,
        response_time_ms: float,
        is_error: bool = False,
    ) -> None:
        """Record a request to an endpoint."""
        endpoint = self._endpoints.get(endpoint_id)
        if endpoint:
            endpoint.metrics.record_request(response_time_ms, is_error)
            self._update_health(endpoint)

    def _update_health(self, endpoint: Endpoint) -> None:
        """Update endpoint health based on metrics."""
        if endpoint.metrics.request_count < 10:
            return  # Not enough data

        if endpoint.metrics.error_rate > self._error_threshold:
            endpoint.status = EndpointStatus.UNHEALTHY
        elif endpoint.metrics.error_rate > self._error_threshold / 2:
            endpoint.status = EndpointStatus.DEGRADED
        else:
            endpoint.status = EndpointStatus.HEALTHY

    def mark_healthy(self, endpoint_id: str) -> None:
        """Mark an endpoint as healthy."""
        endpoint = self._endpoints.get(endpoint_id)
        if endpoint:
            endpoint.status = EndpointStatus.HEALTHY

    def mark_unhealthy(self, endpoint_id: str) -> None:
        """Mark an endpoint as unhealthy."""
        endpoint = self._endpoints.get(endpoint_id)
        if endpoint:
            endpoint.status = EndpointStatus.UNHEALTHY

    @property
    def endpoints(self) -> list[Endpoint]:
        """Get all endpoints."""
        return list(self._endpoints.values())

    @property
    def healthy_endpoints(self) -> list[Endpoint]:
        """Get healthy endpoints."""
        return [e for e in self._endpoints.values() if e.is_available]

    @property
    def endpoint_count(self) -> int:
        """Get total endpoint count."""
        return len(self._endpoints)


class SmartRouterBuilder:
    """Fluent builder for SmartRouter."""

    def __init__(self) -> None:
        self._strategy = LoadBalancingStrategy.ROUND_ROBIN
        self._health_check_interval = timedelta(seconds=30)
        self._error_threshold = 0.5
        self._endpoints: list[tuple[str, str, int, dict[str, Any]]] = []

    def strategy(self, strategy: LoadBalancingStrategy) -> "SmartRouterBuilder":
        """Set the load balancing strategy."""
        self._strategy = strategy
        return self

    def round_robin(self) -> "SmartRouterBuilder":
        """Use round-robin strategy."""
        self._strategy = LoadBalancingStrategy.ROUND_ROBIN
        return self

    def random(self) -> "SmartRouterBuilder":
        """Use random strategy."""
        self._strategy = LoadBalancingStrategy.RANDOM
        return self

    def least_connections(self) -> "SmartRouterBuilder":
        """Use least connections strategy."""
        self._strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
        return self

    def weighted(self) -> "SmartRouterBuilder":
        """Use weighted strategy."""
        self._strategy = LoadBalancingStrategy.WEIGHTED
        return self

    def least_response_time(self) -> "SmartRouterBuilder":
        """Use least response time strategy."""
        self._strategy = LoadBalancingStrategy.LEAST_RESPONSE_TIME
        return self

    def ip_hash(self) -> "SmartRouterBuilder":
        """Use IP hash strategy."""
        self._strategy = LoadBalancingStrategy.IP_HASH
        return self

    def health_check_interval(self, interval: timedelta) -> "SmartRouterBuilder":
        """Set health check interval."""
        self._health_check_interval = interval
        return self

    def error_threshold(self, threshold: float) -> "SmartRouterBuilder":
        """Set error threshold for unhealthy status."""
        self._error_threshold = threshold
        return self

    def add_endpoint(
        self,
        endpoint_id: str,
        url: str,
        weight: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> "SmartRouterBuilder":
        """Add an endpoint."""
        self._endpoints.append((endpoint_id, url, weight, metadata or {}))
        return self

    def build(self) -> SmartRouter[Any]:
        """Build the router."""
        router = SmartRouter[Any](
            strategy=self._strategy,
            health_check_interval=self._health_check_interval,
            error_threshold=self._error_threshold,
        )
        for endpoint_id, url, weight, metadata in self._endpoints:
            router.add_endpoint(endpoint_id, url, weight, metadata)
        return router


# Convenience functions
def create_smart_router(
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
) -> SmartRouter[Any]:
    """Create a smart router with the given strategy."""
    return SmartRouter(strategy=strategy)


def create_load_balancer(strategy: LoadBalancingStrategy) -> LoadBalancer:
    """Create a load balancer for the given strategy."""
    balancers = {
        LoadBalancingStrategy.ROUND_ROBIN: RoundRobinBalancer,
        LoadBalancingStrategy.RANDOM: RandomBalancer,
        LoadBalancingStrategy.LEAST_CONNECTIONS: LeastConnectionsBalancer,
        LoadBalancingStrategy.WEIGHTED: WeightedBalancer,
        LoadBalancingStrategy.LEAST_RESPONSE_TIME: LeastResponseTimeBalancer,
        LoadBalancingStrategy.IP_HASH: IPHashBalancer,
    }
    return balancers[strategy]()
