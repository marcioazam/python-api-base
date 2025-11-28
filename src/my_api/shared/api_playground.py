"""API Playground - Interactive interface for testing API endpoints.

**Feature: api-architecture-analysis, Task 10.2: API Playground**
**Validates: Requirements 10.2**

Provides:
- Interactive endpoint testing with authentication
- Request/response history
- Environment variable management
- OpenAPI schema integration
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class HttpMethod(str, Enum):
    """HTTP methods supported by the playground."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class PlaygroundRequest:
    """Represents a request in the playground."""

    method: HttpMethod
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PlaygroundResponse:
    """Represents a response in the playground."""

    status_code: int
    headers: dict[str, str]
    body: Any
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RequestHistoryEntry:
    """Entry in the request history."""

    id: str
    request: PlaygroundRequest
    response: PlaygroundResponse | None
    name: str | None = None
    tags: list[str] = field(default_factory=list)


class EnvironmentVariable(BaseModel):
    """Environment variable for the playground."""

    key: str
    value: str
    is_secret: bool = False
    description: str | None = None


class PlaygroundEnvironment(BaseModel):
    """Environment configuration for the playground."""

    name: str
    base_url: str
    variables: dict[str, EnvironmentVariable] = {}
    auth_token: str | None = None
    default_headers: dict[str, str] = {}


class EndpointInfo(BaseModel):
    """Information about an API endpoint from OpenAPI."""

    path: str
    method: HttpMethod
    summary: str | None = None
    description: str | None = None
    tags: list[str] = []
    parameters: list[dict[str, Any]] = []
    request_body: dict[str, Any] | None = None
    responses: dict[str, dict[str, Any]] = {}


class APIPlayground:
    """Interactive API playground for testing endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """Initialize the playground."""
        self._base_url = base_url
        self._environments: dict[str, PlaygroundEnvironment] = {}
        self._active_environment: str | None = None
        self._history: list[RequestHistoryEntry] = []
        self._endpoints: dict[str, EndpointInfo] = {}
        self._max_history = 100

    @property
    def base_url(self) -> str:
        """Get the current base URL."""
        if self._active_environment and self._active_environment in self._environments:
            return self._environments[self._active_environment].base_url
        return self._base_url

    def add_environment(self, env: PlaygroundEnvironment) -> None:
        """Add an environment configuration."""
        self._environments[env.name] = env

    def set_active_environment(self, name: str) -> bool:
        """Set the active environment."""
        if name in self._environments:
            self._active_environment = name
            return True
        return False

    def get_environment(self, name: str) -> PlaygroundEnvironment | None:
        """Get an environment by name."""
        return self._environments.get(name)

    def list_environments(self) -> list[str]:
        """List all environment names."""
        return list(self._environments.keys())

    def set_variable(self, key: str, value: str, is_secret: bool = False) -> None:
        """Set an environment variable in the active environment."""
        if self._active_environment and self._active_environment in self._environments:
            env = self._environments[self._active_environment]
            env.variables[key] = EnvironmentVariable(key=key, value=value, is_secret=is_secret)

    def get_variable(self, key: str) -> str | None:
        """Get an environment variable value."""
        if self._active_environment and self._active_environment in self._environments:
            env = self._environments[self._active_environment]
            if key in env.variables:
                return env.variables[key].value
        return None


    def interpolate_variables(self, text: str) -> str:
        """Replace {{variable}} placeholders with actual values."""
        import re

        pattern = r"\{\{(\w+)\}\}"

        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            value = self.get_variable(var_name)
            return value if value is not None else match.group(0)

        return re.sub(pattern, replace, text)

    def load_openapi_schema(self, schema: dict[str, Any]) -> int:
        """Load endpoints from an OpenAPI schema."""
        paths = schema.get("paths", {})
        count = 0

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in [m.value for m in HttpMethod]:
                    endpoint_key = f"{method.upper()}:{path}"
                    self._endpoints[endpoint_key] = EndpointInfo(
                        path=path,
                        method=HttpMethod(method.upper()),
                        summary=details.get("summary"),
                        description=details.get("description"),
                        tags=details.get("tags", []),
                        parameters=details.get("parameters", []),
                        request_body=details.get("requestBody"),
                        responses=details.get("responses", {}),
                    )
                    count += 1

        return count

    def get_endpoints(self, tag: str | None = None) -> list[EndpointInfo]:
        """Get all endpoints, optionally filtered by tag."""
        endpoints = list(self._endpoints.values())
        if tag:
            endpoints = [e for e in endpoints if tag in e.tags]
        return endpoints

    def get_endpoint(self, method: HttpMethod, path: str) -> EndpointInfo | None:
        """Get a specific endpoint."""
        key = f"{method.value}:{path}"
        return self._endpoints.get(key)


    def build_request(
        self,
        method: HttpMethod,
        path: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> PlaygroundRequest:
        """Build a request with environment interpolation."""
        # Interpolate path variables
        interpolated_path = self.interpolate_variables(path)

        # Build headers with defaults
        request_headers: dict[str, str] = {}
        if self._active_environment and self._active_environment in self._environments:
            env = self._environments[self._active_environment]
            request_headers.update(env.default_headers)
            if env.auth_token:
                request_headers["Authorization"] = f"Bearer {env.auth_token}"

        if headers:
            for k, v in headers.items():
                request_headers[k] = self.interpolate_variables(v)

        # Interpolate query params
        interpolated_params: dict[str, str] = {}
        if query_params:
            for k, v in query_params.items():
                interpolated_params[k] = self.interpolate_variables(v)

        return PlaygroundRequest(
            method=method,
            path=interpolated_path,
            headers=request_headers,
            query_params=interpolated_params,
            body=body,
        )

    def add_to_history(
        self,
        request: PlaygroundRequest,
        response: PlaygroundResponse | None,
        name: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Add a request/response to history."""
        from my_api.shared.utils.ids import generate_ulid

        entry_id = generate_ulid()
        entry = RequestHistoryEntry(
            id=entry_id,
            request=request,
            response=response,
            name=name,
            tags=tags or [],
        )
        self._history.append(entry)

        # Trim history if needed
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        return entry_id

    def get_history(self, limit: int = 20) -> list[RequestHistoryEntry]:
        """Get recent history entries."""
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear all history."""
        self._history.clear()

    def export_as_curl(self, request: PlaygroundRequest) -> str:
        """Export a request as a curl command."""
        parts = [f"curl -X {request.method.value}"]

        for key, value in request.headers.items():
            parts.append(f'-H "{key}: {value}"')

        url = f"{self.base_url}{request.path}"
        if request.query_params:
            params = "&".join(f"{k}={v}" for k, v in request.query_params.items())
            url = f"{url}?{params}"

        if request.body:
            import json

            parts.append(f"-d '{json.dumps(request.body)}'")

        parts.append(f'"{url}"')
        return " \\\n  ".join(parts)


class PlaygroundBuilder:
    """Fluent builder for configuring the playground."""

    def __init__(self) -> None:
        """Initialize the builder."""
        self._base_url = "http://localhost:8000"
        self._environments: list[PlaygroundEnvironment] = []
        self._default_env: str | None = None
        self._max_history = 100

    def with_base_url(self, url: str) -> "PlaygroundBuilder":
        """Set the base URL."""
        self._base_url = url
        return self

    def with_environment(
        self,
        name: str,
        base_url: str,
        variables: dict[str, str] | None = None,
        auth_token: str | None = None,
    ) -> "PlaygroundBuilder":
        """Add an environment."""
        env_vars = {}
        if variables:
            for k, v in variables.items():
                env_vars[k] = EnvironmentVariable(key=k, value=v)

        self._environments.append(
            PlaygroundEnvironment(
                name=name,
                base_url=base_url,
                variables=env_vars,
                auth_token=auth_token,
            )
        )
        return self

    def with_default_environment(self, name: str) -> "PlaygroundBuilder":
        """Set the default active environment."""
        self._default_env = name
        return self

    def with_max_history(self, max_entries: int) -> "PlaygroundBuilder":
        """Set maximum history entries."""
        self._max_history = max_entries
        return self

    def build(self) -> APIPlayground:
        """Build the playground instance."""
        playground = APIPlayground(self._base_url)
        playground._max_history = self._max_history

        for env in self._environments:
            playground.add_environment(env)

        if self._default_env:
            playground.set_active_environment(self._default_env)

        return playground


# Pre-configured playground instances
def create_local_playground() -> APIPlayground:
    """Create a playground configured for local development."""
    return (
        PlaygroundBuilder()
        .with_environment(
            name="local",
            base_url="http://localhost:8000",
            variables={"api_version": "v1"},
        )
        .with_environment(
            name="docker",
            base_url="http://api:8000",
            variables={"api_version": "v1"},
        )
        .with_default_environment("local")
        .build()
    )
