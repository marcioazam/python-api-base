"""JSON-RPC 2.0 support for RPC-style APIs.

Implements JSON-RPC 2.0 specification for remote procedure calls.

**Feature: api-architecture-analysis, Property 3: JSON-RPC support**
**Validates: Requirements 4.5**
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any
from collections.abc import Callable, Awaitable
import json


class JSONRPCErrorCode(IntEnum):
    """Standard JSON-RPC 2.0 error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32099
    SERVER_ERROR_END = -32000


@dataclass(frozen=True, slots=True)
class JSONRPCError:
    """JSON-RPC error object."""

    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result

    @classmethod
    def parse_error(cls, data: Any = None) -> "JSONRPCError":
        """Create a parse error."""
        return cls(JSONRPCErrorCode.PARSE_ERROR, "Parse error", data)

    @classmethod
    def invalid_request(cls, data: Any = None) -> "JSONRPCError":
        """Create an invalid request error."""
        return cls(JSONRPCErrorCode.INVALID_REQUEST, "Invalid Request", data)

    @classmethod
    def method_not_found(cls, method: str) -> "JSONRPCError":
        """Create a method not found error."""
        return cls(JSONRPCErrorCode.METHOD_NOT_FOUND, "Method not found", method)

    @classmethod
    def invalid_params(cls, data: Any = None) -> "JSONRPCError":
        """Create an invalid params error."""
        return cls(JSONRPCErrorCode.INVALID_PARAMS, "Invalid params", data)

    @classmethod
    def internal_error(cls, data: Any = None) -> "JSONRPCError":
        """Create an internal error."""
        return cls(JSONRPCErrorCode.INTERNAL_ERROR, "Internal error", data)


@dataclass(slots=True)
class JSONRPCRequest:
    """JSON-RPC request object."""

    method: str
    params: dict[str, Any] | list[Any] | None = None
    id: str | int | None = None
    jsonrpc: str = "2.0"

    @property
    def is_notification(self) -> bool:
        """Check if this is a notification (no id)."""
        return self.id is None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JSONRPCRequest":
        """Create from dictionary."""
        return cls(
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "JSONRPCRequest":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass(slots=True)
class JSONRPCResponse:
    """JSON-RPC response object."""

    id: str | int | None
    result: Any = None
    error: JSONRPCError | None = None
    jsonrpc: str = "2.0"

    @property
    def is_error(self) -> bool:
        """Check if this is an error response."""
        return self.error is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            result["error"] = self.error.to_dict()
        else:
            result["result"] = self.result
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def success(cls, id: str | int | None, result: Any) -> "JSONRPCResponse":
        """Create a success response."""
        return cls(id=id, result=result)

    @classmethod
    def failure(cls, id: str | int | None, error: JSONRPCError) -> "JSONRPCResponse":
        """Create an error response."""
        return cls(id=id, error=error)


MethodHandler = Callable[..., Awaitable[Any]]


@dataclass(slots=True)
class MethodDescriptor:
    """Descriptor for a registered method."""

    name: str
    handler: MethodHandler
    description: str | None = None
    params_schema: dict[str, Any] | None = None
    result_schema: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for introspection."""
        result: dict[str, Any] = {"name": self.name}
        if self.description:
            result["description"] = self.description
        if self.params_schema:
            result["params"] = self.params_schema
        if self.result_schema:
            result["result"] = self.result_schema
        return result


class JSONRPCRouter:
    """Router for JSON-RPC methods."""

    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        self._methods: dict[str, MethodDescriptor] = {}

    def method(
        self,
        name: str | None = None,
        description: str | None = None,
        params_schema: dict[str, Any] | None = None,
        result_schema: dict[str, Any] | None = None,
    ) -> Callable[[MethodHandler], MethodHandler]:
        """Decorator to register a method."""

        def decorator(func: MethodHandler) -> MethodHandler:
            method_name = name or func.__name__
            full_name = f"{self._prefix}.{method_name}" if self._prefix else method_name
            self._methods[full_name] = MethodDescriptor(
                name=full_name,
                handler=func,
                description=description or func.__doc__,
                params_schema=params_schema,
                result_schema=result_schema,
            )
            return func

        return decorator

    def get_method(self, name: str) -> MethodDescriptor | None:
        """Get a method by name."""
        return self._methods.get(name)

    def list_methods(self) -> list[str]:
        """List all registered method names."""
        return list(self._methods.keys())

    def describe_methods(self) -> list[dict[str, Any]]:
        """Get descriptions of all methods."""
        return [m.to_dict() for m in self._methods.values()]

    async def call(
        self, name: str, params: dict[str, Any] | list[Any] | None = None
    ) -> Any:
        """Call a method by name."""
        method = self._methods.get(name)
        if method is None:
            raise ValueError(f"Method not found: {name}")

        if params is None:
            return await method.handler()
        elif isinstance(params, dict):
            return await method.handler(**params)
        else:
            return await method.handler(*params)


class JSONRPCServer:
    """JSON-RPC server for handling requests."""

    def __init__(self):
        self._routers: list[JSONRPCRouter] = []
        self._methods: dict[str, MethodDescriptor] = {}

    def include_router(self, router: JSONRPCRouter) -> None:
        """Include a router's methods."""
        self._routers.append(router)
        self._methods.update(router._methods)

    def register_method(
        self,
        name: str,
        handler: MethodHandler,
        description: str | None = None,
    ) -> None:
        """Register a method directly."""
        self._methods[name] = MethodDescriptor(
            name=name,
            handler=handler,
            description=description,
        )

    async def handle_request(self, request: JSONRPCRequest) -> JSONRPCResponse | None:
        """Handle a single JSON-RPC request."""
        if request.jsonrpc != "2.0":
            return JSONRPCResponse.failure(
                request.id, JSONRPCError.invalid_request("Invalid JSON-RPC version")
            )

        method = self._methods.get(request.method)
        if method is None:
            if request.is_notification:
                return None
            return JSONRPCResponse.failure(
                request.id, JSONRPCError.method_not_found(request.method)
            )

        try:
            if request.params is None:
                result = await method.handler()
            elif isinstance(request.params, dict):
                result = await method.handler(**request.params)
            else:
                result = await method.handler(*request.params)

            if request.is_notification:
                return None
            return JSONRPCResponse.success(request.id, result)
        except TypeError as e:
            if request.is_notification:
                return None
            return JSONRPCResponse.failure(
                request.id, JSONRPCError.invalid_params(str(e))
            )
        except Exception as e:
            if request.is_notification:
                return None
            return JSONRPCResponse.failure(
                request.id, JSONRPCError.internal_error(str(e))
            )

    async def handle_batch(
        self, requests: list[JSONRPCRequest]
    ) -> list[JSONRPCResponse]:
        """Handle a batch of JSON-RPC requests."""
        responses: list[JSONRPCResponse] = []
        for request in requests:
            response = await self.handle_request(request)
            if response is not None:
                responses.append(response)
        return responses

    async def handle_json(self, json_str: str) -> str:
        """Handle a JSON string request and return JSON response."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return JSONRPCResponse.failure(
                None, JSONRPCError.parse_error(str(e))
            ).to_json()

        if isinstance(data, list):
            if not data:
                return JSONRPCResponse.failure(
                    None, JSONRPCError.invalid_request("Empty batch")
                ).to_json()
            requests = [JSONRPCRequest.from_dict(d) for d in data]
            responses = await self.handle_batch(requests)
            if not responses:
                return ""
            return json.dumps([r.to_dict() for r in responses])
        else:
            request = JSONRPCRequest.from_dict(data)
            response = await self.handle_request(request)
            if response is None:
                return ""
            return response.to_json()

    def list_methods(self) -> list[str]:
        """List all registered method names."""
        return list(self._methods.keys())
