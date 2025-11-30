"""API versioning infrastructure.

**Feature: api-base-improvements**
**Validates: Requirements 5.1, 5.2, 5.5**
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class APIVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"


@dataclass
class VersionConfig:
    """Configuration for an API version.

    Attributes:
        version: The API version.
        deprecated: Whether this version is deprecated.
        sunset_date: Date when this version will be removed.
        deprecation_message: Custom deprecation message.
    """

    version: APIVersion
    deprecated: bool = False
    sunset_date: datetime | None = None
    deprecation_message: str | None = None


class VersionedRouter:
    """Router wrapper that adds version prefix and metadata.

    Provides a convenient way to create versioned API routers
    with automatic deprecation headers.
    """

    def __init__(
        self,
        version: APIVersion,
        config: VersionConfig | None = None,
        prefix: str = "/api",
        **router_kwargs: Any,
    ) -> None:
        """Initialize versioned router.

        Args:
            version: API version for this router.
            config: Version configuration.
            prefix: Base API prefix.
            **router_kwargs: Additional kwargs for APIRouter.
        """
        self.version = version
        self.config = config or VersionConfig(version=version)
        self.prefix = f"{prefix}/{version.value}"

        # Create the underlying router
        self._router = APIRouter(
            prefix=self.prefix,
            **router_kwargs,
        )

    @property
    def router(self) -> APIRouter:
        """Get the underlying FastAPI router."""
        return self._router

    def include_router(
        self,
        router: APIRouter,
        **kwargs: Any,
    ) -> None:
        """Include a sub-router.

        Args:
            router: Router to include.
            **kwargs: Additional kwargs for include_router.
        """
        self._router.include_router(router, **kwargs)

    def get(self, path: str, **kwargs: Any) -> Any:
        """Register a GET endpoint."""
        return self._router.get(path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        """Register a POST endpoint."""
        return self._router.post(path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        """Register a PUT endpoint."""
        return self._router.put(path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        """Register a PATCH endpoint."""
        return self._router.patch(path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        """Register a DELETE endpoint."""
        return self._router.delete(path, **kwargs)


class DeprecationHeaderMiddleware(BaseHTTPMiddleware):
    """Middleware that adds deprecation headers for deprecated API versions.

    Adds the following headers for deprecated versions:
    - Deprecation: RFC 8594 deprecation header
    - Sunset: Date when the API version will be removed
    - X-API-Deprecation-Info: Custom deprecation message
    """

    def __init__(
        self,
        app: Any,
        version_configs: dict[str, VersionConfig] | None = None,
    ) -> None:
        """Initialize deprecation middleware.

        Args:
            app: ASGI application.
            version_configs: Map of version string to config.
        """
        super().__init__(app)
        self._configs = version_configs or {}

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Add deprecation headers if applicable."""
        response = await call_next(request)

        # Extract version from path
        path = request.url.path
        version = self._extract_version(path)

        if version and version in self._configs:
            config = self._configs[version]
            if config.deprecated:
                # Add RFC 8594 Deprecation header
                response.headers["Deprecation"] = "true"

                # Add Sunset header if date is set
                if config.sunset_date:
                    sunset_str = config.sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                    response.headers["Sunset"] = sunset_str

                # Add custom deprecation info
                if config.deprecation_message:
                    response.headers["X-API-Deprecation-Info"] = config.deprecation_message
                else:
                    response.headers["X-API-Deprecation-Info"] = (
                        f"API version {version} is deprecated. "
                        "Please migrate to a newer version."
                    )

        return response

    def _extract_version(self, path: str) -> str | None:
        """Extract API version from request path with strict validation.

        Only accepts versions in format 'v' followed by one or more digits.
        Rejects any potentially dangerous or malformed version strings.

        Args:
            path: Request URL path.

        Returns:
            Version string (e.g., 'v1') or None if not found or invalid.
        """
        import re

        # Strict version pattern: v followed by 1-3 digits only
        version_pattern = re.compile(r"^v\d{1,3}$")

        parts = path.split("/")
        for i, part in enumerate(parts):
            if part == "api" and i + 1 < len(parts):
                version = parts[i + 1]
                # Strict validation to prevent path traversal
                if version_pattern.match(version):
                    return version
        return None


def create_versioned_app_routers(
    versions: list[VersionConfig],
    prefix: str = "/api",
) -> dict[APIVersion, VersionedRouter]:
    """Create versioned routers for multiple API versions.

    Args:
        versions: List of version configurations.
        prefix: Base API prefix.

    Returns:
        Dictionary mapping version to VersionedRouter.
    """
    routers: dict[APIVersion, VersionedRouter] = {}

    for config in versions:
        routers[config.version] = VersionedRouter(
            version=config.version,
            config=config,
            prefix=prefix,
        )

    return routers
