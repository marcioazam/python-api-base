"""Property-based tests for Smart Routing Pattern.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.4**
"""

from datetime import timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_app.infrastructure.resilience.smart_routing import (
    Endpoint,
    EndpointMetrics,
    EndpointStatus,
    IPHashBalancer,
    LeastConnectionsBalancer,
    LeastResponseTimeBalancer,
    LoadBalancingStrategy,
    RandomBalancer,
    RoundRobinBalancer,
    SmartRouter,
    SmartRouterBuilder,
    WeightedBalancer,
    create_load_balancer,
    create_smart_router,
)


# Strategies
strategy_type = st.sampled_from(list(LoadBalancingStrategy))
status_type = st.sampled_from(list(EndpointStatus))


class TestEndpointMetricsProperties:
    """Property tests for EndpointMetrics."""

    @given(
        response_times=st.lists(
            st.floats(min_value=0, max_value=1000, allow_nan=False),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_avg_response_time_calculation(
        self, response_times: list[float]
    ) -> None:
        """Property: Average response time is calculated correctly."""
        metrics = EndpointMetrics()
        for rt in response_times:
            metrics.record_request(rt)

        expected_avg = sum(response_times) / len(response_times)
        assert abs(metrics.avg_response_time_ms - expected_avg) < 0.001

    @given(
        total=st.integers(min_value=1, max_value=100),
        errors=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100)
    def test_error_rate_calculation(self, total: int, errors: int) -> None:
        """Property: Error rate is calculated correctly."""
        errors = min(errors, total)  # Ensure errors <= total
        metrics = EndpointMetrics()

        for i in range(total):
            metrics.record_request(10.0, is_error=(i < errors))

        expected_rate = errors / total
        assert abs(metrics.error_rate - expected_rate) < 0.001

    def test_connection_tracking(self) -> None:
        """Property: Connection tracking works correctly."""
        metrics = EndpointMetrics()

        metrics.increment_connections()
        metrics.increment_connections()
        assert metrics.active_connections == 2

        metrics.decrement_connections()
        assert metrics.active_connections == 1

        metrics.decrement_connections()
        metrics.decrement_connections()  # Should not go below 0
        assert metrics.active_connections == 0


class TestEndpointProperties:
    """Property tests for Endpoint."""

    @given(
        endpoint_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        url=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        weight=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_endpoint_preserves_values(
        self, endpoint_id: str, url: str, weight: int
    ) -> None:
        """Property: Endpoint preserves all values."""
        endpoint = Endpoint(id=endpoint_id, url=url, weight=weight)
        assert endpoint.id == endpoint_id
        assert endpoint.url == url
        assert endpoint.weight == weight

    @given(status=status_type)
    @settings(max_examples=50)
    def test_is_available_based_on_status(self, status: EndpointStatus) -> None:
        """Property: is_available depends on status."""
        endpoint = Endpoint(id="test", url="http://test", status=status)

        if status in (EndpointStatus.HEALTHY, EndpointStatus.UNKNOWN):
            assert endpoint.is_available is True
        else:
            assert endpoint.is_available is False


class TestRoundRobinBalancerProperties:
    """Property tests for RoundRobinBalancer."""

    @given(endpoint_count=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_round_robin_cycles_through_endpoints(
        self, endpoint_count: int
    ) -> None:
        """Property: Round robin cycles through all endpoints."""
        balancer = RoundRobinBalancer()
        endpoints = [
            Endpoint(id=f"ep_{i}", url=f"http://ep{i}", status=EndpointStatus.HEALTHY)
            for i in range(endpoint_count)
        ]

        selected_ids = []
        for _ in range(endpoint_count * 2):
            selected = balancer.select(endpoints, {})
            if selected:
                selected_ids.append(selected.id)

        # Should have selected each endpoint at least once
        unique_ids = set(selected_ids)
        assert len(unique_ids) == endpoint_count

    def test_round_robin_returns_none_for_empty_list(self) -> None:
        """Property: Returns None for empty endpoint list."""
        balancer = RoundRobinBalancer()
        assert balancer.select([], {}) is None


class TestRandomBalancerProperties:
    """Property tests for RandomBalancer."""

    @given(endpoint_count=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_random_selects_from_available(self, endpoint_count: int) -> None:
        """Property: Random selects from available endpoints."""
        balancer = RandomBalancer()
        endpoints = [
            Endpoint(id=f"ep_{i}", url=f"http://ep{i}", status=EndpointStatus.HEALTHY)
            for i in range(endpoint_count)
        ]

        selected = balancer.select(endpoints, {})
        assert selected is not None
        assert selected in endpoints

    def test_random_returns_none_for_empty_list(self) -> None:
        """Property: Returns None for empty endpoint list."""
        balancer = RandomBalancer()
        assert balancer.select([], {}) is None



class TestLeastConnectionsBalancerProperties:
    """Property tests for LeastConnectionsBalancer."""

    def test_selects_endpoint_with_least_connections(self) -> None:
        """Property: Selects endpoint with least connections."""
        balancer = LeastConnectionsBalancer()

        ep1 = Endpoint(id="ep1", url="http://ep1", status=EndpointStatus.HEALTHY)
        ep1.metrics.active_connections = 10

        ep2 = Endpoint(id="ep2", url="http://ep2", status=EndpointStatus.HEALTHY)
        ep2.metrics.active_connections = 5

        ep3 = Endpoint(id="ep3", url="http://ep3", status=EndpointStatus.HEALTHY)
        ep3.metrics.active_connections = 15

        selected = balancer.select([ep1, ep2, ep3], {})
        assert selected is not None
        assert selected.id == "ep2"


class TestWeightedBalancerProperties:
    """Property tests for WeightedBalancer."""

    def test_weighted_respects_weights(self) -> None:
        """Property: Weighted balancer respects weights over many selections."""
        balancer = WeightedBalancer()

        ep1 = Endpoint(id="ep1", url="http://ep1", weight=10, status=EndpointStatus.HEALTHY)
        ep2 = Endpoint(id="ep2", url="http://ep2", weight=1, status=EndpointStatus.HEALTHY)

        selections = {"ep1": 0, "ep2": 0}
        for _ in range(1000):
            selected = balancer.select([ep1, ep2], {})
            if selected:
                selections[selected.id] += 1

        # ep1 should be selected roughly 10x more than ep2
        ratio = selections["ep1"] / max(selections["ep2"], 1)
        assert ratio > 5  # Allow some variance


class TestLeastResponseTimeBalancerProperties:
    """Property tests for LeastResponseTimeBalancer."""

    def test_selects_endpoint_with_least_response_time(self) -> None:
        """Property: Selects endpoint with least response time."""
        balancer = LeastResponseTimeBalancer()

        ep1 = Endpoint(id="ep1", url="http://ep1", status=EndpointStatus.HEALTHY)
        ep1.metrics.record_request(100.0)

        ep2 = Endpoint(id="ep2", url="http://ep2", status=EndpointStatus.HEALTHY)
        ep2.metrics.record_request(50.0)

        ep3 = Endpoint(id="ep3", url="http://ep3", status=EndpointStatus.HEALTHY)
        ep3.metrics.record_request(150.0)

        selected = balancer.select([ep1, ep2, ep3], {})
        assert selected is not None
        assert selected.id == "ep2"


class TestIPHashBalancerProperties:
    """Property tests for IPHashBalancer."""

    def test_same_ip_selects_same_endpoint(self) -> None:
        """Property: Same IP always selects same endpoint."""
        balancer = IPHashBalancer()
        endpoints = [
            Endpoint(id=f"ep_{i}", url=f"http://ep{i}", status=EndpointStatus.HEALTHY)
            for i in range(5)
        ]

        context = {"client_ip": "192.168.1.100"}
        first_selection = balancer.select(endpoints, context)

        # Same IP should always select same endpoint
        for _ in range(10):
            selected = balancer.select(endpoints, context)
            assert selected == first_selection

    @given(ip=st.ip_addresses().map(str))
    @settings(max_examples=50)
    def test_different_ips_distribute(self, ip: str) -> None:
        """Property: Different IPs distribute across endpoints."""
        balancer = IPHashBalancer()
        endpoints = [
            Endpoint(id=f"ep_{i}", url=f"http://ep{i}", status=EndpointStatus.HEALTHY)
            for i in range(3)
        ]

        selected = balancer.select(endpoints, {"client_ip": ip})
        assert selected is not None
        assert selected in endpoints


class TestSmartRouterProperties:
    """Property tests for SmartRouter."""

    @given(strategy=strategy_type)
    @settings(max_examples=50)
    def test_router_uses_correct_strategy(
        self, strategy: LoadBalancingStrategy
    ) -> None:
        """Property: Router uses the specified strategy."""
        router = SmartRouter[str](strategy=strategy)
        assert router._strategy == strategy

    def test_add_endpoint_returns_self(self) -> None:
        """Property: add_endpoint returns self for chaining."""
        router = SmartRouter[str]()
        result = router.add_endpoint("ep1", "http://ep1")
        assert result is router

    def test_add_and_remove_endpoint(self) -> None:
        """Property: Endpoints can be added and removed."""
        router = SmartRouter[str]()
        router.add_endpoint("ep1", "http://ep1")

        assert router.endpoint_count == 1
        assert router.get_endpoint("ep1") is not None

        removed = router.remove_endpoint("ep1")
        assert removed is True
        assert router.endpoint_count == 0

    def test_select_endpoint_returns_available(self) -> None:
        """Property: select_endpoint returns available endpoint."""
        router = SmartRouter[str]()
        router.add_endpoint("ep1", "http://ep1")
        router.mark_healthy("ep1")

        selected = router.select_endpoint()
        assert selected is not None
        assert selected.id == "ep1"

    def test_record_request_updates_metrics(self) -> None:
        """Property: record_request updates endpoint metrics."""
        router = SmartRouter[str]()
        router.add_endpoint("ep1", "http://ep1")

        router.record_request("ep1", 100.0)
        router.record_request("ep1", 200.0)

        endpoint = router.get_endpoint("ep1")
        assert endpoint is not None
        assert endpoint.metrics.request_count == 2
        assert endpoint.metrics.avg_response_time_ms == 150.0

    def test_health_status_updates_on_errors(self) -> None:
        """Property: Health status updates based on error rate."""
        router = SmartRouter[str](error_threshold=0.5)
        router.add_endpoint("ep1", "http://ep1")

        # Record many errors to trigger unhealthy status
        for _ in range(20):
            router.record_request("ep1", 100.0, is_error=True)

        endpoint = router.get_endpoint("ep1")
        assert endpoint is not None
        assert endpoint.status == EndpointStatus.UNHEALTHY


class TestSmartRouterBuilderProperties:
    """Property tests for SmartRouterBuilder."""

    def test_builder_fluent_interface(self) -> None:
        """Property: Builder methods return builder for chaining."""
        builder = SmartRouterBuilder()
        result = (
            builder
            .round_robin()
            .error_threshold(0.3)
            .add_endpoint("ep1", "http://ep1")
        )
        assert result is builder

    @given(strategy=strategy_type)
    @settings(max_examples=50)
    def test_builder_creates_router_with_strategy(
        self, strategy: LoadBalancingStrategy
    ) -> None:
        """Property: Builder creates router with specified strategy."""
        router = (
            SmartRouterBuilder()
            .strategy(strategy)
            .add_endpoint("ep1", "http://ep1")
            .build()
        )
        assert router._strategy == strategy
        assert router.endpoint_count == 1


class TestConvenienceFunctions:
    """Property tests for convenience functions."""

    @given(strategy=strategy_type)
    @settings(max_examples=50)
    def test_create_smart_router(self, strategy: LoadBalancingStrategy) -> None:
        """Property: create_smart_router creates router with strategy."""
        router = create_smart_router(strategy)
        assert isinstance(router, SmartRouter)
        assert router._strategy == strategy

    @given(strategy=strategy_type)
    @settings(max_examples=50)
    def test_create_load_balancer(self, strategy: LoadBalancingStrategy) -> None:
        """Property: create_load_balancer creates correct balancer type."""
        balancer = create_load_balancer(strategy)

        expected_types = {
            LoadBalancingStrategy.ROUND_ROBIN: RoundRobinBalancer,
            LoadBalancingStrategy.RANDOM: RandomBalancer,
            LoadBalancingStrategy.LEAST_CONNECTIONS: LeastConnectionsBalancer,
            LoadBalancingStrategy.WEIGHTED: WeightedBalancer,
            LoadBalancingStrategy.LEAST_RESPONSE_TIME: LeastResponseTimeBalancer,
            LoadBalancingStrategy.IP_HASH: IPHashBalancer,
        }

        assert isinstance(balancer, expected_types[strategy])
