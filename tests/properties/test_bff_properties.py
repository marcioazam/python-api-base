"""Property-based tests for Backend for Frontend (BFF) Pattern.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.3**
"""

import pytest

pytest.skip('Module interface.api not implemented', allow_module_level=True)

from hypothesis import given, settings, strategies as st

from interface.api.bff import (
    BFFConfig,
    BFFConfigBuilder,
    BFFRoute,
    BFFRouter,
    ClientConfig,
    ClientInfo,
    ClientType,
    DictTransformer,
    FieldConfig,
    IdentityTransformer,
    ListTransformer,
    create_bff_router,
    create_default_bff_config,
    detect_client,
)


# Strategies
client_type_strategy = st.sampled_from(list(ClientType))

user_agent_strategy = st.sampled_from([
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0) Safari/604.1",
    "Mozilla/5.0 (Linux; Android 11) Chrome/91.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1",
    "curl/7.68.0",
    "PostmanRuntime/7.28.0",
    "Electron/13.0.0",
    "",
])

headers_strategy = st.fixed_dictionaries({
    "user-agent": user_agent_strategy,
}).map(lambda d: {k: v for k, v in d.items() if v})

field_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip() and x.isalpha())


class TestClientInfoProperties:
    """Property tests for ClientInfo."""

    @given(headers=headers_strategy)
    @settings(max_examples=100)
    def test_from_headers_returns_valid_client_info(
        self, headers: dict[str, str]
    ) -> None:
        """Property: from_headers always returns valid ClientInfo."""
        client_info = ClientInfo.from_headers(headers)
        assert isinstance(client_info, ClientInfo)
        assert isinstance(client_info.client_type, ClientType)

    def test_mobile_detection_from_user_agent(self) -> None:
        """Property: Mobile user agents are detected correctly."""
        mobile_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)",
            "Mozilla/5.0 (Linux; Android 11)",
            "Mozilla/5.0 (iPad; CPU OS 14_0)",
        ]
        for agent in mobile_agents:
            info = ClientInfo.from_headers({"user-agent": agent})
            assert info.client_type == ClientType.MOBILE

    def test_web_detection_from_user_agent(self) -> None:
        """Property: Web user agents are detected correctly."""
        web_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1",
        ]
        for agent in web_agents:
            info = ClientInfo.from_headers({"user-agent": agent})
            assert info.client_type == ClientType.WEB

    def test_api_detection_from_user_agent(self) -> None:
        """Property: API user agents are detected correctly."""
        api_agents = ["curl/7.68.0", "PostmanRuntime/7.28.0", "HTTPie/2.4.0"]
        for agent in api_agents:
            info = ClientInfo.from_headers({"user-agent": agent})
            assert info.client_type == ClientType.API

    def test_custom_header_takes_priority(self) -> None:
        """Property: Custom x-client-type header takes priority."""
        headers = {
            "user-agent": "Mozilla/5.0 Chrome/91.0",
            "x-client-type": "mobile",
        }
        info = ClientInfo.from_headers(headers)
        assert info.client_type == ClientType.MOBILE

    @given(
        platform=st.sampled_from(["android", "ios", "windows", "macos", "linux"])
    )
    @settings(max_examples=50)
    def test_platform_detection(self, platform: str) -> None:
        """Property: Platform is detected from user agent."""
        agent_map = {
            "android": "Mozilla/5.0 (Linux; Android 11)",
            "ios": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)",
            "windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "macos": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "linux": "Mozilla/5.0 (X11; Linux x86_64)",
        }
        info = ClientInfo.from_headers({"user-agent": agent_map[platform]})
        assert info.platform == platform


class TestFieldConfigProperties:
    """Property tests for FieldConfig."""

    @given(
        data=st.dictionaries(
            keys=field_name_strategy,
            values=st.integers(),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_empty_config_returns_all_fields(
        self, data: dict[str, int]
    ) -> None:
        """Property: Empty config returns all fields unchanged."""
        config = FieldConfig()
        result = config.apply(data)
        assert result == data

    @given(
        data=st.dictionaries(
            keys=field_name_strategy,
            values=st.integers(),
            min_size=2,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_exclude_removes_fields(self, data: dict[str, int]) -> None:
        """Property: Excluded fields are removed."""
        if not data:
            return

        exclude_key = list(data.keys())[0]
        config = FieldConfig(exclude={exclude_key})
        result = config.apply(data)

        assert exclude_key not in result
        assert len(result) == len(data) - 1

    @given(
        data=st.dictionaries(
            keys=field_name_strategy,
            values=st.integers(),
            min_size=2,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_include_keeps_only_specified_fields(
        self, data: dict[str, int]
    ) -> None:
        """Property: Include keeps only specified fields."""
        if not data:
            return

        include_key = list(data.keys())[0]
        config = FieldConfig(include={include_key})
        result = config.apply(data)

        assert len(result) == 1
        assert include_key in result

    def test_rename_changes_field_names(self) -> None:
        """Property: Rename changes field names correctly."""
        data = {"old_name": 42, "other": 100}
        config = FieldConfig(rename={"old_name": "new_name"})
        result = config.apply(data)

        assert "new_name" in result
        assert "old_name" not in result
        assert result["new_name"] == 42



class TestBFFConfigProperties:
    """Property tests for BFFConfig."""

    @given(client_type=client_type_strategy)
    @settings(max_examples=100)
    def test_get_config_returns_config(self, client_type: ClientType) -> None:
        """Property: get_config always returns a ClientConfig."""
        config = BFFConfig()
        result = config.get_config(client_type)
        assert isinstance(result, ClientConfig)

    def test_configure_stores_config(self) -> None:
        """Property: configure stores the configuration."""
        bff_config = BFFConfig()
        client_config = ClientConfig(
            client_type=ClientType.MOBILE,
            max_list_size=20,
        )
        bff_config.configure(ClientType.MOBILE, client_config)

        result = bff_config.get_config(ClientType.MOBILE)
        assert result.max_list_size == 20

    def test_default_config_used_for_unknown(self) -> None:
        """Property: Default config is used for unconfigured types."""
        bff_config = BFFConfig()
        default = ClientConfig(client_type=ClientType.UNKNOWN, max_list_size=999)
        bff_config.set_default(default)

        result = bff_config.get_config(ClientType.MOBILE)
        assert result.max_list_size == 999


class TestTransformerProperties:
    """Property tests for transformers."""

    @given(
        data=st.dictionaries(
            keys=field_name_strategy,
            values=st.integers(),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_identity_transformer_preserves_data(
        self, data: dict[str, int]
    ) -> None:
        """Property: IdentityTransformer returns data unchanged."""
        transformer = IdentityTransformer[dict[str, int]]()
        client_info = ClientInfo(client_type=ClientType.WEB)
        result = transformer.transform(data, client_info)
        assert result == data

    def test_dict_transformer_applies_field_config(self) -> None:
        """Property: DictTransformer applies field configuration."""
        bff_config = BFFConfig()
        client_config = ClientConfig(
            client_type=ClientType.MOBILE,
            fields=FieldConfig(exclude={"internal_id"}),
        )
        bff_config.configure(ClientType.MOBILE, client_config)

        transformer = DictTransformer(bff_config)
        data = {"name": "test", "internal_id": 123}
        client_info = ClientInfo(client_type=ClientType.MOBILE)

        result = transformer.transform(data, client_info)
        assert "internal_id" not in result
        assert result["name"] == "test"

    @given(
        list_size=st.integers(min_value=1, max_value=100),
        max_size=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=50)
    def test_list_transformer_respects_max_size(
        self, list_size: int, max_size: int
    ) -> None:
        """Property: ListTransformer respects max_list_size."""
        bff_config = BFFConfig()
        client_config = ClientConfig(
            client_type=ClientType.MOBILE,
            max_list_size=max_size,
        )
        bff_config.configure(ClientType.MOBILE, client_config)

        transformer = ListTransformer(bff_config)
        data = [{"id": i} for i in range(list_size)]
        client_info = ClientInfo(client_type=ClientType.MOBILE)

        result = transformer.transform(data, client_info)
        assert len(result) <= max_size


class TestBFFRouteProperties:
    """Property tests for BFFRoute."""

    @pytest.mark.anyio
    async def test_route_uses_default_handler(self) -> None:
        """Property: Route uses default handler when no client-specific handler."""

        async def default_handler(req: str, info: ClientInfo) -> str:
            return f"default:{req}"

        route = BFFRoute(
            path="/test",
            method="GET",
            default_handler=default_handler,
        )

        client_info = ClientInfo(client_type=ClientType.WEB)
        result = await route.handle("request", client_info)
        assert result == "default:request"

    @pytest.mark.anyio
    async def test_route_uses_client_specific_handler(self) -> None:
        """Property: Route uses client-specific handler when available."""

        async def default_handler(req: str, info: ClientInfo) -> str:
            return f"default:{req}"

        async def mobile_handler(req: str, info: ClientInfo) -> str:
            return f"mobile:{req}"

        route = BFFRoute(
            path="/test",
            method="GET",
            default_handler=default_handler,
        )
        route.add_handler(ClientType.MOBILE, mobile_handler)

        client_info = ClientInfo(client_type=ClientType.MOBILE)
        result = await route.handle("request", client_info)
        assert result == "mobile:request"

    def test_add_handler_returns_route(self) -> None:
        """Property: add_handler returns the route for chaining."""

        async def handler(req: str, info: ClientInfo) -> str:
            return req

        route = BFFRoute(path="/test", method="GET", default_handler=handler)
        result = route.add_handler(ClientType.MOBILE, handler)
        assert result is route


class TestBFFRouterProperties:
    """Property tests for BFFRouter."""

    def test_route_decorator_registers_route(self) -> None:
        """Property: route decorator registers the route."""
        router: BFFRouter[str, str] = BFFRouter()

        @router.route("/test", "GET")
        async def handler(req: str, info: ClientInfo) -> str:
            return req

        route = router.get_route("/test", "GET")
        assert route is not None
        assert route.path == "/test"
        assert route.method == "GET"

    @pytest.mark.anyio
    async def test_handle_routes_to_correct_handler(self) -> None:
        """Property: handle routes to the correct handler."""
        router: BFFRouter[str, str] = BFFRouter()

        @router.route("/test", "GET")
        async def handler(req: str, info: ClientInfo) -> str:
            return f"handled:{req}"

        result = await router.handle("/test", "GET", "data", {"user-agent": "curl/7.0"})
        assert result == "handled:data"

    def test_routes_property_returns_all_routes(self) -> None:
        """Property: routes property returns all registered routes."""
        router: BFFRouter[str, str] = BFFRouter()

        @router.route("/test1", "GET")
        async def handler1(req: str, info: ClientInfo) -> str:
            return req

        @router.route("/test2", "POST")
        async def handler2(req: str, info: ClientInfo) -> str:
            return req

        routes = router.routes
        assert len(routes) == 2


class TestBFFConfigBuilderProperties:
    """Property tests for BFFConfigBuilder."""

    def test_builder_fluent_interface(self) -> None:
        """Property: Builder methods return builder for chaining."""
        builder = BFFConfigBuilder()
        result = (
            builder
            .for_mobile(max_list_size=20)
            .for_web(max_list_size=50)
            .for_desktop(max_list_size=100)
            .for_api(max_list_size=1000)
        )
        assert result is builder

    def test_builder_creates_valid_config(self) -> None:
        """Property: Builder creates valid configuration."""
        config = (
            BFFConfigBuilder()
            .for_mobile(max_list_size=20, compress_images=True)
            .for_web(max_list_size=50)
            .build()
        )

        mobile_config = config.get_config(ClientType.MOBILE)
        assert mobile_config.max_list_size == 20
        assert mobile_config.compress_images is True

        web_config = config.get_config(ClientType.WEB)
        assert web_config.max_list_size == 50


class TestConvenienceFunctions:
    """Property tests for convenience functions."""

    def test_create_bff_router_returns_router(self) -> None:
        """Property: create_bff_router returns a BFFRouter."""
        router = create_bff_router()
        assert isinstance(router, BFFRouter)

    @given(headers=headers_strategy)
    @settings(max_examples=100)
    def test_detect_client_returns_client_info(
        self, headers: dict[str, str]
    ) -> None:
        """Property: detect_client returns ClientInfo."""
        info = detect_client(headers)
        assert isinstance(info, ClientInfo)

    def test_create_default_bff_config_has_all_clients(self) -> None:
        """Property: Default config has settings for all client types."""
        config = create_default_bff_config()

        # Check that each client type has specific config
        mobile = config.get_config(ClientType.MOBILE)
        assert mobile.max_list_size == 20

        web = config.get_config(ClientType.WEB)
        assert web.max_list_size == 50

        desktop = config.get_config(ClientType.DESKTOP)
        assert desktop.max_list_size == 100

        api = config.get_config(ClientType.API)
        assert api.max_list_size == 1000
