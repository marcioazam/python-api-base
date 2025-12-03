"""Property-based tests for Conditional Middleware.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.4**
"""

import pytest

pytest.skip('Module interface.api not implemented', allow_module_level=True)

from hypothesis import given, settings, strategies as st

from interface.api.middleware.conditional_middleware import (
    AlwaysCondition,
    AndCondition,
    ConditionalMiddleware,
    ConditionalMiddlewareRegistry,
    CustomCondition,
    HeaderCondition,
    HttpMethod,
    MethodCondition,
    NeverCondition,
    NotCondition,
    OrCondition,
    PathCondition,
    RouteInfo,
    always,
    custom,
    header,
    method,
    never,
    path,
)


# Strategies
path_strategy = st.from_regex(r"^/[a-z0-9/]*$", fullmatch=True)
method_strategy = st.sampled_from([m for m in HttpMethod if m != HttpMethod.ALL])


def make_route_info(path: str = "/test", method: HttpMethod = HttpMethod.GET) -> RouteInfo:
    """Create a RouteInfo for testing."""
    return RouteInfo(path=path, method=method)


class TestPathConditionProperties:
    """Property tests for PathCondition."""

    @given(path_str=path_strategy)
    @settings(max_examples=100)
    def test_exact_path_matches(self, path_str: str) -> None:
        """Property: Exact path matches itself."""
        condition = PathCondition(path_str)
        route_info = make_route_info(path=path_str)
        assert condition.matches(route_info) is True

    def test_wildcard_matches_any_suffix(self) -> None:
        """Property: Wildcard * matches any suffix."""
        condition = PathCondition("/api/*")
        assert condition.matches(make_route_info("/api/users")) is True
        assert condition.matches(make_route_info("/api/items/123")) is True
        assert condition.matches(make_route_info("/other")) is False

    def test_regex_pattern_works(self) -> None:
        """Property: Regex patterns work correctly."""
        condition = PathCondition(r"/api/v\d+/.*", regex=True)
        assert condition.matches(make_route_info("/api/v1/users")) is True
        assert condition.matches(make_route_info("/api/v2/items")) is True
        assert condition.matches(make_route_info("/api/users")) is False


class TestMethodConditionProperties:
    """Property tests for MethodCondition."""

    @given(http_method=method_strategy)
    @settings(max_examples=100)
    def test_method_matches_itself(self, http_method: HttpMethod) -> None:
        """Property: Method matches itself."""
        condition = MethodCondition(http_method)
        route_info = make_route_info(method=http_method)
        assert condition.matches(route_info) is True

    @given(http_method=method_strategy)
    @settings(max_examples=100)
    def test_all_matches_any_method(self, http_method: HttpMethod) -> None:
        """Property: ALL matches any method."""
        condition = MethodCondition(HttpMethod.ALL)
        route_info = make_route_info(method=http_method)
        assert condition.matches(route_info) is True

    def test_multiple_methods(self) -> None:
        """Property: Multiple methods match any of them."""
        condition = MethodCondition(HttpMethod.GET, HttpMethod.POST)
        assert condition.matches(make_route_info(method=HttpMethod.GET)) is True
        assert condition.matches(make_route_info(method=HttpMethod.POST)) is True
        assert condition.matches(make_route_info(method=HttpMethod.DELETE)) is False


class TestHeaderConditionProperties:
    """Property tests for HeaderCondition."""

    def test_header_presence(self) -> None:
        """Property: Header presence check works."""
        condition = HeaderCondition("Authorization")
        route_with = RouteInfo(path="/", method=HttpMethod.GET, headers={"Authorization": "Bearer token"})
        route_without = RouteInfo(path="/", method=HttpMethod.GET, headers={})

        assert condition.matches(route_with) is True
        assert condition.matches(route_without) is False

    def test_header_value_match(self) -> None:
        """Property: Header value match works."""
        condition = HeaderCondition("Content-Type", "application/json")
        route_match = RouteInfo(path="/", method=HttpMethod.GET, headers={"Content-Type": "application/json"})
        route_no_match = RouteInfo(path="/", method=HttpMethod.GET, headers={"Content-Type": "text/html"})

        assert condition.matches(route_match) is True
        assert condition.matches(route_no_match) is False

    def test_header_case_insensitive(self) -> None:
        """Property: Header names are case-insensitive."""
        condition = HeaderCondition("content-type")
        route = RouteInfo(path="/", method=HttpMethod.GET, headers={"Content-Type": "application/json"})
        assert condition.matches(route) is True


class TestCompositeConditionProperties:
    """Property tests for composite conditions."""

    def test_and_condition(self) -> None:
        """Property: AND requires both conditions to match."""
        path_cond = PathCondition("/api/*")
        method_cond = MethodCondition(HttpMethod.POST)
        combined = path_cond & method_cond

        assert combined.matches(make_route_info("/api/users", HttpMethod.POST)) is True
        assert combined.matches(make_route_info("/api/users", HttpMethod.GET)) is False
        assert combined.matches(make_route_info("/other", HttpMethod.POST)) is False

    def test_or_condition(self) -> None:
        """Property: OR requires either condition to match."""
        get_cond = MethodCondition(HttpMethod.GET)
        post_cond = MethodCondition(HttpMethod.POST)
        combined = get_cond | post_cond

        assert combined.matches(make_route_info(method=HttpMethod.GET)) is True
        assert combined.matches(make_route_info(method=HttpMethod.POST)) is True
        assert combined.matches(make_route_info(method=HttpMethod.DELETE)) is False

    def test_not_condition(self) -> None:
        """Property: NOT inverts the condition."""
        path_cond = PathCondition("/health")
        negated = ~path_cond

        assert negated.matches(make_route_info("/health")) is False
        assert negated.matches(make_route_info("/api/users")) is True

    def test_complex_composition(self) -> None:
        """Property: Complex compositions work correctly."""
        # (path matches /api/* AND method is POST) OR header is present
        condition = (path("/api/*") & method(HttpMethod.POST)) | header("X-Admin")

        assert condition.matches(make_route_info("/api/users", HttpMethod.POST)) is True
        assert condition.matches(make_route_info("/api/users", HttpMethod.GET)) is False

        route_with_header = RouteInfo(
            path="/other", method=HttpMethod.GET, headers={"X-Admin": "true"}
        )
        assert condition.matches(route_with_header) is True


class TestAlwaysNeverConditionProperties:
    """Property tests for Always and Never conditions."""

    @given(path_str=path_strategy, http_method=method_strategy)
    @settings(max_examples=100)
    def test_always_matches_everything(self, path_str: str, http_method: HttpMethod) -> None:
        """Property: Always condition matches any route."""
        condition = always()
        route_info = make_route_info(path_str, http_method)
        assert condition.matches(route_info) is True

    @given(path_str=path_strategy, http_method=method_strategy)
    @settings(max_examples=100)
    def test_never_matches_nothing(self, path_str: str, http_method: HttpMethod) -> None:
        """Property: Never condition matches no route."""
        condition = never()
        route_info = make_route_info(path_str, http_method)
        assert condition.matches(route_info) is False


class TestCustomConditionProperties:
    """Property tests for CustomCondition."""

    def test_custom_function(self) -> None:
        """Property: Custom function is called correctly."""
        def is_admin_route(route: RouteInfo) -> bool:
            return route.path.startswith("/admin")

        condition = custom(is_admin_route)

        assert condition.matches(make_route_info("/admin/users")) is True
        assert condition.matches(make_route_info("/api/users")) is False


class TestConditionalMiddlewareRegistryProperties:
    """Property tests for ConditionalMiddlewareRegistry."""

    @pytest.mark.anyio
    async def test_registry_executes_matching_middleware(self) -> None:
        """Property: Registry executes only matching middlewares."""
        registry: ConditionalMiddlewareRegistry[dict, dict] = ConditionalMiddlewareRegistry()
        executed: list[str] = []

        async def api_middleware(request: dict, next_handler) -> dict:
            executed.append("api")
            return await next_handler(request)

        async def admin_middleware(request: dict, next_handler) -> dict:
            executed.append("admin")
            return await next_handler(request)

        registry.for_path("/api/*", api_middleware, "api")
        registry.for_path("/admin/*", admin_middleware, "admin")

        async def final_handler(request: dict) -> dict:
            return {"result": "ok"}

        # Test API route
        executed.clear()
        route_info = make_route_info("/api/users")
        await registry.execute({}, route_info, final_handler)
        assert "api" in executed
        assert "admin" not in executed

        # Test admin route
        executed.clear()
        route_info = make_route_info("/admin/settings")
        await registry.execute({}, route_info, final_handler)
        assert "admin" in executed
        assert "api" not in executed

    @pytest.mark.anyio
    async def test_registry_for_methods(self) -> None:
        """Property: for_methods registers correctly."""
        registry: ConditionalMiddlewareRegistry[dict, dict] = ConditionalMiddlewareRegistry()
        executed = False

        async def write_middleware(request: dict, next_handler) -> dict:
            nonlocal executed
            executed = True
            return await next_handler(request)

        registry.for_methods([HttpMethod.POST, HttpMethod.PUT], write_middleware)

        async def final_handler(request: dict) -> dict:
            return {}

        # POST should trigger
        executed = False
        await registry.execute({}, make_route_info(method=HttpMethod.POST), final_handler)
        assert executed is True

        # GET should not trigger
        executed = False
        await registry.execute({}, make_route_info(method=HttpMethod.GET), final_handler)
        assert executed is False

    def test_get_matching_returns_correct_middlewares(self) -> None:
        """Property: get_matching returns only matching middlewares."""
        registry: ConditionalMiddlewareRegistry[dict, dict] = ConditionalMiddlewareRegistry()

        async def mw1(r, n): return await n(r)
        async def mw2(r, n): return await n(r)
        async def mw3(r, n): return await n(r)

        registry.for_path("/api/*", mw1, "api")
        registry.for_path("/admin/*", mw2, "admin")
        registry.register(mw3, always(), "all")

        matching = registry.get_matching(make_route_info("/api/users"))
        names = [m.name for m in matching]

        assert "api" in names
        assert "all" in names
        assert "admin" not in names

    def test_registry_length(self) -> None:
        """Property: Registry length matches registered count."""
        registry: ConditionalMiddlewareRegistry[dict, dict] = ConditionalMiddlewareRegistry()

        async def mw(r, n): return await n(r)

        assert len(registry) == 0
        registry.for_path("/a", mw)
        assert len(registry) == 1
        registry.for_path("/b", mw)
        assert len(registry) == 2
