"""Property-based tests for Strangler Fig Pattern.

**Feature: api-architecture-analysis, Property 12: Strangler fig pattern**
**Validates: Requirements 4.3**
"""

import pytest
from hypothesis import given, settings, strategies as st

from my_app.infrastructure.migration.strangler_fig import (
    RouteConfig,
    RoutingDecision,
    RoutingStats,
    RoutingStrategy,
    StranglerRouter,
    create_migration_plan,
)


identifier_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz/_"),
    min_size=1,
    max_size=30,
)


class TestRouteConfig:
    """Tests for RouteConfig."""

    @given(path=identifier_strategy)
    @settings(max_examples=50)
    def test_matches_exact_path(self, path: str):
        """matches_path should match exact path."""
        config = RouteConfig(path_pattern=path, strategy=RoutingStrategy.LEGACY_ONLY)
        assert config.matches_path(path) is True

    def test_matches_wildcard_path(self):
        """matches_path should match wildcard patterns."""
        config = RouteConfig(
            path_pattern="/api/*", strategy=RoutingStrategy.LEGACY_ONLY
        )
        assert config.matches_path("/api/users") is True
        assert config.matches_path("/api/items") is True
        assert config.matches_path("/other/path") is False


class TestRoutingDecision:
    """Tests for RoutingDecision."""

    def test_to_dict(self):
        """to_dict should contain all fields."""
        config = RouteConfig(
            path_pattern="/api/*", strategy=RoutingStrategy.PERCENTAGE
        )
        decision = RoutingDecision(
            route_to_new=True,
            reason="Test reason",
            config=config,
        )
        d = decision.to_dict()
        assert d["route_to_new"] is True
        assert d["reason"] == "Test reason"
        assert d["strategy"] == "percentage"


class TestRoutingStats:
    """Tests for RoutingStats."""

    @given(
        legacy=st.integers(min_value=0, max_value=1000),
        new=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=50)
    def test_new_percentage(self, legacy: int, new: int):
        """new_percentage should calculate correctly."""
        stats = RoutingStats(
            total_requests=legacy + new,
            legacy_requests=legacy,
            new_requests=new,
        )
        if legacy + new > 0:
            expected = new / (legacy + new) * 100
            assert abs(stats.new_percentage - expected) < 0.001
        else:
            assert stats.new_percentage == 0.0

    def test_to_dict(self):
        """to_dict should contain all fields."""
        stats = RoutingStats(
            total_requests=100,
            legacy_requests=60,
            new_requests=40,
        )
        d = stats.to_dict()
        assert d["total_requests"] == 100
        assert d["new_percentage"] == 40.0


class TestStranglerRouter:
    """Tests for StranglerRouter."""

    @pytest.mark.asyncio
    async def test_route_to_legacy_by_default(self):
        """Should route to legacy by default."""
        legacy_called = False
        new_called = False

        async def legacy_handler(ctx):
            nonlocal legacy_called
            legacy_called = True
            return "legacy"

        async def new_handler(ctx):
            nonlocal new_called
            new_called = True
            return "new"

        router = StranglerRouter(legacy_handler, new_handler)
        result = await router.route("/api/test", {})
        assert result == "legacy"
        assert legacy_called is True
        assert new_called is False

    @pytest.mark.asyncio
    async def test_route_to_new_with_new_only_strategy(self):
        """Should route to new with NEW_ONLY strategy."""
        async def legacy_handler(ctx):
            return "legacy"

        async def new_handler(ctx):
            return "new"

        router = StranglerRouter(legacy_handler, new_handler)
        router.add_route(
            RouteConfig(path_pattern="/api/*", strategy=RoutingStrategy.NEW_ONLY)
        )
        result = await router.route("/api/test", {})
        assert result == "new"

    @pytest.mark.asyncio
    async def test_route_with_header_based_strategy(self):
        """Should route based on header."""
        async def legacy_handler(ctx):
            return "legacy"

        async def new_handler(ctx):
            return "new"

        router = StranglerRouter(legacy_handler, new_handler)
        router.add_route(
            RouteConfig(
                path_pattern="/api/*",
                strategy=RoutingStrategy.HEADER_BASED,
                header_name="X-Use-New",
                header_value="true",
            )
        )

        result1 = await router.route("/api/test", {"headers": {"X-Use-New": "true"}})
        assert result1 == "new"

        result2 = await router.route("/api/test", {"headers": {}})
        assert result2 == "legacy"

    @pytest.mark.asyncio
    async def test_route_with_user_based_strategy(self):
        """Should route based on user."""
        async def legacy_handler(ctx):
            return "legacy"

        async def new_handler(ctx):
            return "new"

        router = StranglerRouter(legacy_handler, new_handler)
        router.add_route(
            RouteConfig(
                path_pattern="/api/*",
                strategy=RoutingStrategy.USER_BASED,
                allowed_users={"user1", "user2"},
            )
        )

        result1 = await router.route("/api/test", {"user_id": "user1"})
        assert result1 == "new"

        result2 = await router.route("/api/test", {"user_id": "user3"})
        assert result2 == "legacy"

    def test_add_and_remove_route(self):
        """Should add and remove routes."""
        async def handler(ctx):
            return "result"

        router = StranglerRouter(handler, handler)
        router.add_route(
            RouteConfig(path_pattern="/api/*", strategy=RoutingStrategy.NEW_ONLY)
        )
        assert router.get_route("/api/*") is not None

        result = router.remove_route("/api/*")
        assert result is True
        assert router.get_route("/api/*") is None

    def test_update_percentage(self):
        """Should update percentage for route."""
        async def handler(ctx):
            return "result"

        router = StranglerRouter(handler, handler)
        router.add_route(
            RouteConfig(
                path_pattern="/api/*",
                strategy=RoutingStrategy.PERCENTAGE,
                new_percentage=10.0,
            )
        )

        result = router.update_percentage("/api/*", 50.0)
        assert result is True
        route = router.get_route("/api/*")
        assert route is not None
        assert route.new_percentage == 50.0

    def test_get_stats(self):
        """Should return routing stats."""
        async def handler(ctx):
            return "result"

        router = StranglerRouter(handler, handler)
        router.add_route(
            RouteConfig(path_pattern="/api/*", strategy=RoutingStrategy.LEGACY_ONLY)
        )
        stats = router.get_stats("/api/*")
        assert "total_requests" in stats

    def test_list_routes(self):
        """Should list all routes."""
        async def handler(ctx):
            return "result"

        router = StranglerRouter(handler, handler)
        router.add_route(
            RouteConfig(path_pattern="/api/v1/*", strategy=RoutingStrategy.LEGACY_ONLY)
        )
        router.add_route(
            RouteConfig(path_pattern="/api/v2/*", strategy=RoutingStrategy.NEW_ONLY)
        )
        routes = router.list_routes()
        assert len(routes) == 2


class TestCreateMigrationPlan:
    """Tests for create_migration_plan."""

    def test_creates_phases(self):
        """Should create specified number of phases."""
        plan = create_migration_plan(["/api/*"], phases=4)
        assert len(plan) == 4

    def test_phases_have_increasing_percentages(self):
        """Phases should have increasing percentages."""
        plan = create_migration_plan(["/api/*"], phases=4)
        percentages = [p["percentage"] for p in plan]
        assert percentages == [25, 50, 75, 100]

    def test_phases_include_routes(self):
        """Phases should include specified routes."""
        routes = ["/api/users/*", "/api/items/*"]
        plan = create_migration_plan(routes, phases=2)
        for phase in plan:
            assert phase["routes"] == routes
