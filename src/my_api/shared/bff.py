"""Backend for Frontend (BFF) Pattern Implementation.

This module provides BFF routing for optimized responses per client type
(mobile, web, desktop, API).

**Feature: api-architecture-analysis**
**Validates: Requirements 4.3**
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Generic, Protocol, TypeVar, runtime_checkable


RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")
DataT = TypeVar("DataT")


class ClientType(Enum):
    """Supported client types."""

    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    API = "api"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
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
class ResponseTransformer(Protocol[DataT]):
    """Protocol for transforming responses based on client type."""

    def transform(self, data: DataT, client_info: ClientInfo) -> Any: ...


class BaseTransformer(ABC, Generic[DataT]):
    """Base class for response transformers."""

    @abstractmethod
    def transform(self, data: DataT, client_info: ClientInfo) -> Any:
        """Transform data for the client."""
        ...


class IdentityTransformer(BaseTransformer[DataT]):
    """Transformer that returns data unchanged."""

    def transform(self, data: DataT, client_info: ClientInfo) -> DataT:
        return data



@dataclass
class FieldConfig:
    """Configuration for field inclusion/exclusion."""

    include: set[str] = field(default_factory=set)
    exclude: set[str] = field(default_factory=set)
    rename: dict[str, str] = field(default_factory=dict)

    def apply(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply field configuration to data."""
        result = {}

        for key, value in data.items():
            # Check exclusion
            if self.exclude and key in self.exclude:
                continue

            # Check inclusion (if specified, only include listed fields)
            if self.include and key not in self.include:
                continue

            # Apply rename
            new_key = self.rename.get(key, key)
            result[new_key] = value

        return result


@dataclass
class ClientConfig:
    """Configuration for a specific client type."""

    client_type: ClientType
    fields: FieldConfig = field(default_factory=FieldConfig)
    max_list_size: int = 100
    include_metadata: bool = True
    compress_images: bool = False
    image_quality: int = 80
    pagination_style: str = "offset"  # offset, cursor
    date_format: str = "iso"  # iso, unix, relative


class BFFConfig:
    """Configuration for BFF routing."""

    def __init__(self) -> None:
        self._configs: dict[ClientType, ClientConfig] = {}
        self._default_config = ClientConfig(client_type=ClientType.UNKNOWN)

    def configure(self, client_type: ClientType, config: ClientConfig) -> "BFFConfig":
        """Configure settings for a client type."""
        self._configs[client_type] = config
        return self

    def get_config(self, client_type: ClientType) -> ClientConfig:
        """Get configuration for a client type."""
        return self._configs.get(client_type, self._default_config)

    def set_default(self, config: ClientConfig) -> "BFFConfig":
        """Set default configuration."""
        self._default_config = config
        return self


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


# Handler type alias
HandlerFunc = Callable[[RequestT, ClientInfo], Awaitable[ResponseT]]


@dataclass
class BFFRoute(Generic[RequestT, ResponseT]):
    """A BFF route with client-specific handlers."""

    path: str
    method: str
    default_handler: HandlerFunc[RequestT, ResponseT]
    client_handlers: dict[ClientType, HandlerFunc[RequestT, ResponseT]] = field(
        default_factory=dict
    )

    def add_handler(
        self,
        client_type: ClientType,
        handler: HandlerFunc[RequestT, ResponseT],
    ) -> "BFFRoute[RequestT, ResponseT]":
        """Add a client-specific handler."""
        self.client_handlers[client_type] = handler
        return self

    def get_handler(self, client_type: ClientType) -> HandlerFunc[RequestT, ResponseT]:
        """Get the appropriate handler for the client type."""
        return self.client_handlers.get(client_type, self.default_handler)

    async def handle(self, request: RequestT, client_info: ClientInfo) -> ResponseT:
        """Handle the request with the appropriate handler."""
        handler = self.get_handler(client_info.client_type)
        return await handler(request, client_info)



class BFFRouter(Generic[RequestT, ResponseT]):
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


class BFFConfigBuilder:
    """Builder for BFF configuration."""

    def __init__(self) -> None:
        self._config = BFFConfig()

    def for_mobile(
        self,
        max_list_size: int = 20,
        exclude_fields: set[str] | None = None,
        compress_images: bool = True,
    ) -> "BFFConfigBuilder":
        """Configure mobile client settings."""
        config = ClientConfig(
            client_type=ClientType.MOBILE,
            fields=FieldConfig(exclude=exclude_fields or set()),
            max_list_size=max_list_size,
            compress_images=compress_images,
            image_quality=60,
            pagination_style="cursor",
        )
        self._config.configure(ClientType.MOBILE, config)
        return self

    def for_web(
        self,
        max_list_size: int = 50,
        exclude_fields: set[str] | None = None,
    ) -> "BFFConfigBuilder":
        """Configure web client settings."""
        config = ClientConfig(
            client_type=ClientType.WEB,
            fields=FieldConfig(exclude=exclude_fields or set()),
            max_list_size=max_list_size,
            include_metadata=True,
            pagination_style="offset",
        )
        self._config.configure(ClientType.WEB, config)
        return self

    def for_desktop(
        self,
        max_list_size: int = 100,
        include_metadata: bool = True,
    ) -> "BFFConfigBuilder":
        """Configure desktop client settings."""
        config = ClientConfig(
            client_type=ClientType.DESKTOP,
            max_list_size=max_list_size,
            include_metadata=include_metadata,
        )
        self._config.configure(ClientType.DESKTOP, config)
        return self

    def for_api(
        self,
        max_list_size: int = 1000,
        date_format: str = "iso",
    ) -> "BFFConfigBuilder":
        """Configure API client settings."""
        config = ClientConfig(
            client_type=ClientType.API,
            max_list_size=max_list_size,
            include_metadata=True,
            date_format=date_format,
        )
        self._config.configure(ClientType.API, config)
        return self

    def build(self) -> BFFConfig:
        """Build the configuration."""
        return self._config


# Convenience functions
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
