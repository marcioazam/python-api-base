"""bff service."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from collections.abc import Awaitable, Callable
from .enums import ClientType
from .models import BFFRoute
from .config import BFFConfig, BFFConfigBuilder

type HandlerFunc[RequestT, ResponseT] = Callable[[RequestT, "ClientInfo"], Awaitable[ResponseT]]


@dataclass(frozen=True, slots=True)
class ClientInfo:
    """Information about the client making the request."""

    client_type: ClientType
    platform: str = ""  # ios, android, windows, macos, linux, browser
    version: str = ""
    user_agent: str = ""
    accept_language: str = ""
    screen_size: str = ""  # small, medium, large
    connection_type: str = ""  # wifi, cellular, ethernet

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> "ClientInfo":
        """Create ClientInfo from request headers."""
        user_agent = headers.get("user-agent", "").lower()
        client_type = cls._detect_client_type(user_agent, headers)
        platform = cls._detect_platform(user_agent)

        return cls(
            client_type=client_type,
            platform=platform,
            version=headers.get("x-client-version", ""),
            user_agent=headers.get("user-agent", ""),
            accept_language=headers.get("accept-language", ""),
            screen_size=headers.get("x-screen-size", ""),
            connection_type=headers.get("x-connection-type", ""),
        )

    @staticmethod
    def _detect_client_type(user_agent: str, headers: dict[str, str]) -> ClientType:
        """Detect client type from user agent and headers."""
        # Check custom header first
        custom_client = headers.get("x-client-type", "").lower()
        if custom_client:
            mapping = {
                "web": ClientType.WEB,
                "mobile": ClientType.MOBILE,
                "desktop": ClientType.DESKTOP,
                "api": ClientType.API,
            }
            return mapping.get(custom_client, ClientType.UNKNOWN)

        # Detect from user agent
        if any(m in user_agent for m in ["android", "iphone", "ipad", "mobile"]):
            return ClientType.MOBILE
        if any(d in user_agent for d in ["electron", "tauri"]):
            return ClientType.DESKTOP
        if any(b in user_agent for b in ["mozilla", "chrome", "safari", "firefox", "edge"]):
            return ClientType.WEB
        if any(a in user_agent for a in ["curl", "httpie", "postman", "insomnia"]):
            return ClientType.API

        return ClientType.UNKNOWN

    @staticmethod
    def _detect_platform(user_agent: str) -> str:
        """Detect platform from user agent."""
        if "android" in user_agent:
            return "android"
        if "iphone" in user_agent or "ipad" in user_agent:
            return "ios"
        if "windows" in user_agent:
            return "windows"
        if "macintosh" in user_agent or "mac os" in user_agent:
            return "macos"
        if "linux" in user_agent:
            return "linux"
        return "unknown"

@runtime_checkable
class ResponseTransformer[DataT](Protocol):
    """Protocol for transforming responses based on client type."""

    def transform(self, data: DataT, client_info: ClientInfo) -> Any: ...

class BaseTransformer[DataT](ABC):
    """Base class for response transformers."""

    @abstractmethod
    def transform(self, data: DataT, client_info: ClientInfo) -> Any:
        """Transform data for the client."""
        ...

class IdentityTransformer[DataT](BaseTransformer[DataT]):
    """Transformer that returns data unchanged."""

    def transform(self, data: DataT, client_info: ClientInfo) -> DataT:
        return data

class DictTransformer(BaseTransformer[dict[str, Any]]):
    """Transformer for dictionary data based on client config."""

    def __init__(self, bff_config: BFFConfig) -> None:
        self._config = bff_config

    def transform(self, data: dict[str, Any], client_info: ClientInfo) -> dict[str, Any]:
        """Transform dictionary data for the client."""
        config = self._config.get_config(client_info.client_type)
        return config.fields.apply(data)

class ListTransformer(BaseTransformer[list[dict[str, Any]]]):
    """Transformer for list data with pagination limits."""

    def __init__(self, bff_config: BFFConfig) -> None:
        self._config = bff_config

    def transform(
        self, data: list[dict[str, Any]], client_info: ClientInfo
    ) -> list[dict[str, Any]]:
        """Transform list data for the client."""
        config = self._config.get_config(client_info.client_type)

        # Apply max list size
        limited_data = data[: config.max_list_size]

        # Apply field config to each item
        return [config.fields.apply(item) for item in limited_data]

class BFFRouter[RequestT, ResponseT]:
    """Router for BFF pattern with client-specific routing."""

    def __init__(self, config: BFFConfig | None = None) -> None:
        self._config = config or BFFConfig()
        self._routes: dict[str, BFFRoute[RequestT, ResponseT]] = {}

    def route(
        self,
        path: str,
        method: str = "GET",
    ) -> Callable[
        [HandlerFunc[RequestT, ResponseT]],
        BFFRoute[RequestT, ResponseT],
    ]:
        """Decorator to register a default route handler."""

        def decorator(
            handler: HandlerFunc[RequestT, ResponseT],
        ) -> BFFRoute[RequestT, ResponseT]:
            route_key = f"{method.upper()}:{path}"
            route = BFFRoute(
                path=path,
                method=method.upper(),
                default_handler=handler,
            )
            self._routes[route_key] = route
            return route

        return decorator

    def for_client(
        self,
        path: str,
        method: str,
        client_type: ClientType,
    ) -> Callable[
        [HandlerFunc[RequestT, ResponseT]],
        HandlerFunc[RequestT, ResponseT],
    ]:
        """Decorator to register a client-specific handler."""

        def decorator(
            handler: HandlerFunc[RequestT, ResponseT],
        ) -> HandlerFunc[RequestT, ResponseT]:
            route_key = f"{method.upper()}:{path}"
            if route_key in self._routes:
                self._routes[route_key].add_handler(client_type, handler)
            return handler

        return decorator

    def get_route(self, path: str, method: str) -> BFFRoute[RequestT, ResponseT] | None:
        """Get a route by path and method."""
        route_key = f"{method.upper()}:{path}"
        return self._routes.get(route_key)

    async def handle(
        self,
        path: str,
        method: str,
        request: RequestT,
        headers: dict[str, str],
    ) -> ResponseT:
        """Handle a request with BFF routing."""
        route = self.get_route(path, method)
        if not route:
            raise ValueError(f"No route found for {method} {path}")

        client_info = ClientInfo.from_headers(headers)
        return await route.handle(request, client_info)

    @property
    def routes(self) -> list[BFFRoute[RequestT, ResponseT]]:
        """Get all registered routes."""
        return list(self._routes.values())

def create_bff_router(config: BFFConfig | None = None) -> BFFRouter[Any, Any]:
    """Create a BFF router with optional configuration."""
    return BFFRouter(config)

def detect_client(headers: dict[str, str]) -> ClientInfo:
    """Detect client information from headers."""
    return ClientInfo.from_headers(headers)

def create_default_bff_config() -> BFFConfig:
    """Create a default BFF configuration."""
    return (
        BFFConfigBuilder()
        .for_mobile(max_list_size=20, compress_images=True)
        .for_web(max_list_size=50)
        .for_desktop(max_list_size=100)
        .for_api(max_list_size=1000)
        .build()
    )
