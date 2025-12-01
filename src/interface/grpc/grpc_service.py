"""gRPC Service Module.

Provides generic gRPC service implementation with
type-safe request/response handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections.abc import Callable


class GRPCStatus(Enum):
    """gRPC status codes."""
    OK = 0
    CANCELLED = 1
    UNKNOWN = 2
    INVALID_ARGUMENT = 3
    DEADLINE_EXCEEDED = 4
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    PERMISSION_DENIED = 7
    RESOURCE_EXHAUSTED = 8
    FAILED_PRECONDITION = 9
    ABORTED = 10
    OUT_OF_RANGE = 11
    UNIMPLEMENTED = 12
    INTERNAL = 13
    UNAVAILABLE = 14
    DATA_LOSS = 15
    UNAUTHENTICATED = 16


class MethodType(Enum):
    """gRPC method types."""
    UNARY = "unary"
    SERVER_STREAMING = "server_streaming"
    CLIENT_STREAMING = "client_streaming"
    BIDIRECTIONAL = "bidirectional"


@dataclass(frozen=True, slots=True)
class GRPCError:
    """gRPC error response."""
    code: GRPCStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "message": self.message, "details": self.details}


@dataclass
class GRPCMetadata:
    """gRPC call metadata."""
    headers: dict[str, str] = field(default_factory=dict)
    trailers: dict[str, str] = field(default_factory=dict)
    deadline: datetime | None = None

    def add_header(self, key: str, value: str) -> None:
        self._validate_key(key)
        self.headers[key.lower()] = value

    def add_trailer(self, key: str, value: str) -> None:
        self._validate_key(key)
        self.trailers[key.lower()] = value

    def get_header(self, key: str) -> str | None:
        return self.headers.get(key.lower())

    def _validate_key(self, key: str) -> None:
        if not key or not key.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid metadata key: {key}")


@dataclass
class GRPCContext:
    """Context for gRPC call."""
    metadata: GRPCMetadata = field(default_factory=GRPCMetadata)
    peer: str = ""
    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True

    def is_active(self) -> bool:
        return not self.cancelled


@dataclass
class MethodDescriptor:
    """Descriptor for a gRPC method."""
    name: str
    method_type: MethodType
    input_type: str
    output_type: str
    handler: Callable[..., Any] | None = None

    @property
    def full_name(self) -> str:
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.method_type.value,
                "input": self.input_type, "output": self.output_type}


@dataclass
class ServiceDescriptor:
    """Descriptor for a gRPC service."""
    name: str
    package: str = ""
    methods: list[MethodDescriptor] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.package}.{self.name}" if self.package else self.name

    def add_method(self, method: MethodDescriptor) -> None:
        self.methods.append(method)

    def get_method(self, name: str) -> MethodDescriptor | None:
        for m in self.methods:
            if m.name == name:
                return m
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "package": self.package,
                "full_name": self.full_name,
                "methods": [m.to_dict() for m in self.methods]}


class GRPCService[T]:
    """Generic gRPC service base class."""
    def __init__(self, descriptor: ServiceDescriptor) -> None:
        self._descriptor = descriptor
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._interceptors: list[Callable[..., Any]] = []

    @property
    def descriptor(self) -> ServiceDescriptor:
        return self._descriptor

    @property
    def name(self) -> str:
        return self._descriptor.name

    def register_handler(self, method_name: str, handler: Callable[..., Any]) -> None:
        method = self._descriptor.get_method(method_name)
        if method is None:
            raise ValueError(f"Method {method_name} not found in service")
        self._handlers[method_name] = handler
        method.handler = handler

    def add_interceptor(self, interceptor: Callable[..., Any]) -> None:
        self._interceptors.append(interceptor)

    def get_handler(self, method_name: str) -> Callable[..., Any] | None:
        return self._handlers.get(method_name)

    def call(self, method_name: str, request: Any, context: GRPCContext) -> Any:
        handler = self.get_handler(method_name)
        if handler is None:
            raise GRPCError(GRPCStatus.UNIMPLEMENTED, f"Method {method_name} not implemented")
        if context.cancelled:
            raise GRPCError(GRPCStatus.CANCELLED, "Call cancelled")
        for interceptor in self._interceptors:
            request = interceptor(request, context)
        return handler(request, context)


class ServiceRegistry:
    """Registry for gRPC services."""
    def __init__(self) -> None:
        self._services: dict[str, GRPCService[Any]] = {}

    def register(self, service: GRPCService[Any]) -> None:
        self._services[service.descriptor.full_name] = service

    def get(self, name: str) -> GRPCService[Any] | None:
        return self._services.get(name)

    def list_services(self) -> list[str]:
        return list(self._services.keys())

    def get_all_methods(self) -> list[tuple[str, MethodDescriptor]]:
        methods: list[tuple[str, MethodDescriptor]] = []
        for svc_name, svc in self._services.items():
            for method in svc.descriptor.methods:
                methods.append((svc_name, method))
        return methods


@dataclass
class ProtoField:
    """Protobuf field definition."""
    name: str
    number: int
    field_type: str
    repeated: bool = False
    optional: bool = False

    def to_proto(self) -> str:
        prefix = "repeated " if self.repeated else ("optional " if self.optional else "")
        return f"  {prefix}{self.field_type} {self.name} = {self.number};"


@dataclass
class ProtoMessage:
    """Protobuf message definition."""
    name: str
    fields: list[ProtoField] = field(default_factory=list)

    def add_field(self, name: str, number: int, field_type: str, **kwargs: Any) -> None:
        self.fields.append(ProtoField(name=name, number=number, field_type=field_type, **kwargs))

    def to_proto(self) -> str:
        lines = [f"message {self.name} {{"]
        for f in self.fields:
            lines.append(f.to_proto())
        lines.append("}")
        return "\n".join(lines)


class ProtoGenerator:
    """Generates protobuf definitions."""
    def __init__(self, package: str = "") -> None:
        self._package = package
        self._messages: list[ProtoMessage] = []
        self._services: list[ServiceDescriptor] = []

    def add_message(self, message: ProtoMessage) -> None:
        self._messages.append(message)

    def add_service(self, service: ServiceDescriptor) -> None:
        self._services.append(service)

    def generate(self) -> str:
        lines = ['syntax = "proto3";', ""]
        if self._package:
            lines.append(f"package {self._package};")
            lines.append("")
        for msg in self._messages:
            lines.append(msg.to_proto())
            lines.append("")
        for svc in self._services:
            lines.append(f"service {svc.name} {{")
            for method in svc.methods:
                rpc_type = self._get_rpc_signature(method)
                lines.append(f"  rpc {method.name}({rpc_type[0]}) returns ({rpc_type[1]});")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)

    def _get_rpc_signature(self, method: MethodDescriptor) -> tuple[str, str]:
        input_type = method.input_type
        output_type = method.output_type
        if method.method_type == MethodType.CLIENT_STREAMING:
            input_type = f"stream {input_type}"
        elif method.method_type == MethodType.SERVER_STREAMING:
            output_type = f"stream {output_type}"
        elif method.method_type == MethodType.BIDIRECTIONAL:
            input_type = f"stream {input_type}"
            output_type = f"stream {output_type}"
        return (input_type, output_type)


def create_service_descriptor(name: str, package: str = "") -> ServiceDescriptor:
    """Create a new service descriptor."""
    return ServiceDescriptor(name=name, package=package)


def create_unary_method(name: str, input_type: str, output_type: str) -> MethodDescriptor:
    """Create a unary method descriptor."""
    return MethodDescriptor(name=name, method_type=MethodType.UNARY,
                           input_type=input_type, output_type=output_type)


def create_streaming_method(name: str, input_type: str, output_type: str,
                           method_type: MethodType) -> MethodDescriptor:
    """Create a streaming method descriptor."""
    return MethodDescriptor(name=name, method_type=method_type,
                           input_type=input_type, output_type=output_type)
