"""Mock Server - Development server with automatic mock generation.

**Feature: api-architecture-analysis, Task 10.3: Mock Server**
**Validates: Requirements 8.1**

Provides:
- Automatic mock response generation from OpenAPI schemas
- Configurable response delays for testing
- Request recording for verification
- Stateful mock data management
"""

import random
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from collections.abc import Callable

from pydantic import BaseModel


class MockResponseMode(str, Enum):
    """Mode for generating mock responses."""

    STATIC = "static"
    RANDOM = "random"
    SEQUENTIAL = "sequential"
    CALLBACK = "callback"


@dataclass
class MockEndpoint:
    """Configuration for a mocked endpoint."""

    path: str
    method: str
    response_body: Any = None
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    delay_ms: int = 0
    mode: MockResponseMode = MockResponseMode.STATIC
    responses: list[Any] = field(default_factory=list)
    callback: Callable[..., Any] | None = None
    _response_index: int = 0


@dataclass
class RecordedRequest:
    """A recorded incoming request."""

    path: str
    method: str
    headers: dict[str, str]
    query_params: dict[str, str]
    body: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class MockResponse(BaseModel):
    """Response from the mock server."""

    status_code: int
    headers: dict[str, str]
    body: Any
    delay_ms: int = 0


class MockDataGenerator:
    """Generates mock data based on JSON Schema types."""

    def __init__(self, seed: int | None = None) -> None:
        """Initialize with optional seed for reproducibility."""
        if seed is not None:
            random.seed(seed)

    def generate(self, schema: dict[str, Any]) -> Any:
        """Generate mock data from a JSON schema."""
        schema_type = schema.get("type", "string")

        if schema_type == "object":
            return self._generate_object(schema)
        elif schema_type == "array":
            return self._generate_array(schema)
        elif schema_type == "string":
            return self._generate_string(schema)
        elif schema_type == "integer":
            return self._generate_integer(schema)
        elif schema_type == "number":
            return self._generate_number(schema)
        elif schema_type == "boolean":
            return random.choice([True, False])
        elif schema_type == "null":
            return None
        return "mock_value"

    def _generate_object(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate a mock object."""
        result: dict[str, Any] = {}
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            result[prop_name] = self.generate(prop_schema)
        return result

    def _generate_array(self, schema: dict[str, Any]) -> list[Any]:
        """Generate a mock array."""
        items_schema = schema.get("items", {"type": "string"})
        min_items = schema.get("minItems", 1)
        max_items = schema.get("maxItems", 5)
        count = random.randint(min_items, max_items)
        return [self.generate(items_schema) for _ in range(count)]

    def _generate_string(self, schema: dict[str, Any]) -> str:
        """Generate a mock string."""
        if "enum" in schema:
            return random.choice(schema["enum"])
        if schema.get("format") == "date-time":
            return datetime.now(UTC).isoformat()
        if schema.get("format") == "email":
            return f"user{random.randint(1, 999)}@example.com"
        if schema.get("format") == "uuid":
            import uuid
            return str(uuid.uuid4())
        min_len = schema.get("minLength", 5)
        max_len = schema.get("maxLength", 20)
        length = random.randint(min_len, max_len)
        return "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=length))

    def _generate_integer(self, schema: dict[str, Any]) -> int:
        """Generate a mock integer."""
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", 1000)
        return random.randint(minimum, maximum)

    def _generate_number(self, schema: dict[str, Any]) -> float:
        """Generate a mock number."""
        minimum = schema.get("minimum", 0.0)
        maximum = schema.get("maximum", 1000.0)
        return round(random.uniform(minimum, maximum), 2)


class MockServer:
    """Mock server for development and testing."""

    def __init__(self) -> None:
        """Initialize the mock server."""
        self._endpoints: dict[str, MockEndpoint] = {}
        self._recorded_requests: list[RecordedRequest] = []
        self._data_generator = MockDataGenerator()
        self._state: dict[str, Any] = {}
        self._max_recorded = 1000

    def register(
        self,
        path: str,
        method: str = "GET",
        response_body: Any = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        delay_ms: int = 0,
    ) -> "MockServer":
        """Register a mock endpoint with static response."""
        key = f"{method.upper()}:{path}"
        self._endpoints[key] = MockEndpoint(
            path=path,
            method=method.upper(),
            response_body=response_body,
            status_code=status_code,
            headers=headers or {"Content-Type": "application/json"},
            delay_ms=delay_ms,
            mode=MockResponseMode.STATIC,
        )
        return self

    def register_sequential(
        self,
        path: str,
        method: str,
        responses: list[tuple[int, Any]],
    ) -> "MockServer":
        """Register endpoint with sequential responses."""
        key = f"{method.upper()}:{path}"
        self._endpoints[key] = MockEndpoint(
            path=path,
            method=method.upper(),
            responses=[{"status": s, "body": b} for s, b in responses],
            mode=MockResponseMode.SEQUENTIAL,
            headers={"Content-Type": "application/json"},
        )
        return self

    def register_callback(
        self,
        path: str,
        method: str,
        callback: Callable[[RecordedRequest], tuple[int, Any]],
    ) -> "MockServer":
        """Register endpoint with callback handler."""
        key = f"{method.upper()}:{path}"
        self._endpoints[key] = MockEndpoint(
            path=path,
            method=method.upper(),
            callback=callback,
            mode=MockResponseMode.CALLBACK,
            headers={"Content-Type": "application/json"},
        )
        return self

    def _match_path(self, registered: str, actual: str) -> dict[str, str] | None:
        """Match path with parameters, returns extracted params or None."""
        pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", registered)
        match = re.fullmatch(pattern, actual)
        if match:
            return match.groupdict()
        return None

    def _find_endpoint(self, method: str, path: str) -> tuple[MockEndpoint | None, dict[str, str]]:
        """Find matching endpoint and extract path params."""
        exact_key = f"{method}:{path}"
        if exact_key in self._endpoints:
            return self._endpoints[exact_key], {}

        for key, endpoint in self._endpoints.items():
            if not key.startswith(f"{method}:"):
                continue
            params = self._match_path(endpoint.path, path)
            if params is not None:
                return endpoint, params

        return None, {}


    def handle_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        body: Any = None,
    ) -> MockResponse:
        """Handle an incoming request and return mock response."""
        request = RecordedRequest(
            path=path,
            method=method.upper(),
            headers=headers or {},
            query_params=query_params or {},
            body=body,
        )
        self._record_request(request)

        endpoint, path_params = self._find_endpoint(method.upper(), path)
        if endpoint is None:
            return MockResponse(
                status_code=404,
                headers={"Content-Type": "application/json"},
                body={"error": "Not Found", "path": path},
            )

        return self._generate_response(endpoint, request, path_params)

    def _generate_response(
        self,
        endpoint: MockEndpoint,
        request: RecordedRequest,
        path_params: dict[str, str],
    ) -> MockResponse:
        """Generate response based on endpoint configuration."""
        if endpoint.mode == MockResponseMode.STATIC:
            return MockResponse(
                status_code=endpoint.status_code,
                headers=endpoint.headers,
                body=endpoint.response_body,
                delay_ms=endpoint.delay_ms,
            )

        elif endpoint.mode == MockResponseMode.SEQUENTIAL:
            if endpoint.responses:
                resp = endpoint.responses[endpoint._response_index % len(endpoint.responses)]
                endpoint._response_index += 1
                return MockResponse(
                    status_code=resp.get("status", 200),
                    headers=endpoint.headers,
                    body=resp.get("body"),
                    delay_ms=endpoint.delay_ms,
                )

        elif endpoint.mode == MockResponseMode.CALLBACK and endpoint.callback:
            status, body = endpoint.callback(request)
            return MockResponse(
                status_code=status,
                headers=endpoint.headers,
                body=body,
                delay_ms=endpoint.delay_ms,
            )

        return MockResponse(
            status_code=200,
            headers=endpoint.headers,
            body=None,
        )

    def _record_request(self, request: RecordedRequest) -> None:
        """Record a request for later verification."""
        self._recorded_requests.append(request)
        if len(self._recorded_requests) > self._max_recorded:
            self._recorded_requests = self._recorded_requests[-self._max_recorded:]

    def get_recorded_requests(
        self,
        path: str | None = None,
        method: str | None = None,
    ) -> list[RecordedRequest]:
        """Get recorded requests, optionally filtered."""
        requests = self._recorded_requests
        if path:
            requests = [r for r in requests if r.path == path]
        if method:
            requests = [r for r in requests if r.method == method.upper()]
        return requests

    def clear_recorded_requests(self) -> None:
        """Clear all recorded requests."""
        self._recorded_requests.clear()

    def reset(self) -> None:
        """Reset all endpoints and recorded requests."""
        self._endpoints.clear()
        self._recorded_requests.clear()
        self._state.clear()

    def set_state(self, key: str, value: Any) -> None:
        """Set stateful data."""
        self._state[key] = value

    def get_state(self, key: str) -> Any:
        """Get stateful data."""
        return self._state.get(key)

    def load_from_openapi(self, schema: dict[str, Any]) -> int:
        """Load mock endpoints from OpenAPI schema."""
        paths = schema.get("paths", {})
        count = 0

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                    continue

                responses = details.get("responses", {})
                success_response = responses.get("200") or responses.get("201") or {}
                content = success_response.get("content", {})
                json_content = content.get("application/json", {})
                response_schema = json_content.get("schema", {})

                mock_body = self._data_generator.generate(response_schema) if response_schema else {}
                status = 200 if "200" in responses else 201 if "201" in responses else 200

                self.register(path, method.upper(), mock_body, status)
                count += 1

        return count
