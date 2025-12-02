"""Generic API versioning with PEP 695 type parameters.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 21.1, 21.2, 21.3, 21.4, 21.5**
"""

import functools
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel


class VersionFormat(Enum):
    """API version format."""

    URL_PREFIX = "url_prefix"
    HEADER = "header"
    QUERY_PARAM = "query_param"
    ACCEPT_HEADER = "accept_header"


@dataclass(frozen=True, slots=True)
class ApiVersion[TVersion]:
    """Generic API version with typed version identifier.

    Type Parameters:
        TVersion: Version type (str, int, tuple, etc.)

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 21.1**
    """

    version: TVersion
    deprecated: bool = False
    sunset_date: datetime | None = None
    successor: TVersion | None = None


@dataclass
class VersionConfig[TVersion]:
    """Configuration for API versioning.

    Type Parameters:
        TVersion: Version type.
    """

    format: VersionFormat = VersionFormat.URL_PREFIX
    header_name: str = "X-API-Version"
    query_param: str = "api_version"
    default_version: TVersion | None = None
    supported_versions: list[TVersion] = field(default_factory=list)


class VersionedRouter[TVersion]:
    """Generic versioned router with URL prefix support.

    Type Parameters:
        TVersion: Version type (str, int, etc.)

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 21.1**
    """

    def __init__(
        self,
        version: ApiVersion[TVersion],
        prefix: str = "",
        tags: list[str] | None = None,
    ) -> None:
        self._version = version
        version_str = str(version.version)
        full_prefix = f"/v{version_str}{prefix}"
        self._router = APIRouter(prefix=full_prefix, tags=tags or [f"v{version_str}"])
        self._deprecated_endpoints: set[str] = set()

    @property
    def router(self) -> APIRouter:
        """Get the FastAPI router."""
        return self._router

    @property
    def version(self) -> ApiVersion[TVersion]:
        """Get the API version."""
        return self._version

    def deprecated_route(
        self,
        path: str,
        *,
        sunset_date: datetime | None = None,
        successor_version: TVersion | None = None,
        message: str | None = None,
    ) -> Callable:
        """Mark a route as deprecated.

        **Validates: Requirements 21.2**

        Args:
            path: Route path.
            sunset_date: When this endpoint will be removed.
            successor_version: Version where replacement exists.
            message: Deprecation message.

        Returns:
            Decorator function.
        """

        def decorator(func: Callable) -> Callable:
            self._deprecated_endpoints.add(path)

            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Issue deprecation warning
                warn_msg = message or f"Endpoint {path} is deprecated"
                if successor_version:
                    warn_msg += f". Use v{successor_version} instead"
                warnings.warn(warn_msg, DeprecationWarning, stacklevel=2)

                # Call original function
                response = await func(*args, **kwargs)

                # Add headers if response available
                if "response" in kwargs and isinstance(kwargs["response"], Response):
                    resp: Response = kwargs["response"]
                    resp.headers["Deprecation"] = "true"
                    if sunset_date:
                        resp.headers["Sunset"] = sunset_date.strftime(
                            "%a, %d %b %Y %H:%M:%S GMT"
                        )
                    if message:
                        resp.headers["X-Deprecation-Notice"] = message

                return response

            return wrapper

        return decorator


def deprecated[T](
    *,
    sunset_date: datetime | None = None,
    message: str | None = None,
    successor: str | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to mark endpoints as deprecated with sunset headers.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 21.2**

    Args:
        sunset_date: When this endpoint will be removed.
        message: Custom deprecation message.
        successor: Path to successor endpoint.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Issue warning
            warn_msg = message or f"Endpoint {func.__name__} is deprecated"
            if successor:
                warn_msg += f". Use {successor} instead"
            warnings.warn(warn_msg, DeprecationWarning, stacklevel=2)

            return await func(*args, **kwargs)

        # Mark as deprecated for OpenAPI
        wrapper.__deprecated__ = True
        wrapper.__sunset_date__ = sunset_date
        wrapper.__deprecation_message__ = message
        return wrapper

    return decorator


@runtime_checkable
class ResponseTransformer[TFrom: BaseModel, TTo: BaseModel](Protocol):
    """Generic response transformer for version migration.

    Type Parameters:
        TFrom: Source response type.
        TTo: Target response type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 21.3**
    """

    def transform(self, source: TFrom) -> TTo:
        """Transform response from one version to another.

        Args:
            source: Source response.

        Returns:
            Transformed response.
        """
        ...

    def get_field_mapping(self) -> dict[str, str]:
        """Get field mapping from source to target.

        Returns:
            Dictionary mapping source fields to target fields.
        """
        ...


class BaseResponseTransformer[TFrom: BaseModel, TTo: BaseModel]:
    """Base class for response transformers.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 21.3**
    """

    def __init__(
        self,
        target_type: type[TTo],
        field_mapping: dict[str, str] | None = None,
    ) -> None:
        self._target_type = target_type
        self._field_mapping = field_mapping or {}

    def transform(self, source: TFrom) -> TTo:
        """Transform response using field mapping."""
        source_dict = source.model_dump()
        target_dict = {}

        for source_field, target_field in self._field_mapping.items():
            if source_field in source_dict:
                target_dict[target_field] = source_dict[source_field]

        # Copy unmapped fields directly
        for field_name, value in source_dict.items():
            if field_name not in self._field_mapping:
                if field_name in self._target_type.model_fields:
                    target_dict[field_name] = value

        return self._target_type(**target_dict)

    def get_field_mapping(self) -> dict[str, str]:
        """Get field mapping."""
        return self._field_mapping.copy()


class VersionRouter:
    """Router that supports header-based version selection.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 21.4, 21.5**
    """

    def __init__(
        self,
        header_name: str = "X-API-Version",
        default_version: str = "1",
    ) -> None:
        self._header_name = header_name
        self._default_version = default_version
        self._version_routers: dict[str, APIRouter] = {}

    def register_version(self, version: str, router: APIRouter) -> None:
        """Register a router for a specific version."""
        self._version_routers[version] = router

    def get_version_from_request(self, request: Request) -> str:
        """Extract version from request headers."""
        return request.headers.get(self._header_name, self._default_version)

    def get_router_for_version(self, version: str) -> APIRouter | None:
        """Get router for specified version."""
        return self._version_routers.get(version)

    def generate_openapi_for_version(self, version: str) -> dict[str, Any]:
        """Generate OpenAPI spec for specific version.

        **Validates: Requirements 21.5**
        """
        router = self._version_routers.get(version)
        if router is None:
            return {}

        # Generate OpenAPI from router routes
        openapi: dict[str, Any] = {
            "openapi": "3.1.0",
            "info": {
                "title": f"API v{version}",
                "version": version,
            },
            "paths": {},
        }

        for route in router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                path = route.path
                for method in route.methods:
                    if path not in openapi["paths"]:
                        openapi["paths"][path] = {}
                    openapi["paths"][path][method.lower()] = {
                        "summary": getattr(route, "summary", ""),
                        "description": getattr(route, "description", ""),
                    }

        return openapi
