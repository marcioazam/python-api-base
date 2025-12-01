"""Property-based tests for gRPC Service module.

**Feature: api-architecture-analysis, Property 16.1: gRPC Support**
**Validates: Requirements 4.5**
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.my_app.shared.grpc_service import (
    GRPCStatus,
    MethodType,
    GRPCError,
    GRPCMetadata,
    GRPCContext,
    MethodDescriptor,
    ServiceDescriptor,
    GRPCService,
    ServiceRegistry,
    ProtoField,
    ProtoMessage,
    ProtoGenerator,
    create_service_descriptor,
    create_unary_method,
    create_streaming_method,
)


# Strategies
names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1, max_size=30,
)
packages = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="._"),
    min_size=0, max_size=30,
)
header_keys = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1, max_size=20,
)
header_values = st.text(min_size=1, max_size=50)
grpc_statuses = st.sampled_from(list(GRPCStatus))
method_types = st.sampled_from(list(MethodType))
field_numbers = st.integers(min_value=1, max_value=1000)
proto_types = st.sampled_from(["string", "int32", "int64", "bool", "float", "double", "bytes"])


class TestGRPCError:
    """Property tests for GRPCError."""

    @given(code=grpc_statuses, message=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_to_dict_contains_fields(self, code: GRPCStatus, message: str) -> None:
        """to_dict contains all required fields."""
        error = GRPCError(code=code, message=message)
        d = error.to_dict()
        assert d["code"] == code.value
        assert d["message"] == message


class TestGRPCMetadata:
    """Property tests for GRPCMetadata."""

    @given(key=header_keys, value=header_values)
    @settings(max_examples=100)
    def test_add_and_get_header(self, key: str, value: str) -> None:
        """Added header can be retrieved."""
        metadata = GRPCMetadata()
        metadata.add_header(key, value)
        assert metadata.get_header(key) == value

    @given(key=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20), value=header_values)
    @settings(max_examples=100)
    def test_header_case_insensitive(self, key: str, value: str) -> None:
        """Headers are case insensitive."""
        metadata = GRPCMetadata()
        metadata.add_header(key.upper(), value)
        assert metadata.get_header(key.lower()) == value

    @given(key=header_keys)
    @settings(max_examples=100)
    def test_get_nonexistent_header(self, key: str) -> None:
        """Getting nonexistent header returns None."""
        metadata = GRPCMetadata()
        assert metadata.get_header(key) is None


class TestGRPCContext:
    """Property tests for GRPCContext."""

    def test_initial_state(self) -> None:
        """Context starts active."""
        context = GRPCContext()
        assert context.is_active()
        assert not context.cancelled

    def test_cancel(self) -> None:
        """Cancel sets cancelled flag."""
        context = GRPCContext()
        context.cancel()
        assert context.cancelled
        assert not context.is_active()


class TestMethodDescriptor:
    """Property tests for MethodDescriptor."""

    @given(name=names, method_type=method_types, input_type=names, output_type=names)
    @settings(max_examples=100)
    def test_to_dict(self, name: str, method_type: MethodType, input_type: str, output_type: str) -> None:
        """to_dict contains all fields."""
        method = MethodDescriptor(name=name, method_type=method_type,
                                  input_type=input_type, output_type=output_type)
        d = method.to_dict()
        assert d["name"] == name
        assert d["type"] == method_type.value
        assert d["input"] == input_type
        assert d["output"] == output_type

    @given(name=names)
    @settings(max_examples=100)
    def test_full_name(self, name: str) -> None:
        """full_name returns method name."""
        method = MethodDescriptor(name=name, method_type=MethodType.UNARY,
                                  input_type="Request", output_type="Response")
        assert method.full_name == name


class TestServiceDescriptor:
    """Property tests for ServiceDescriptor."""

    @given(name=names, package=packages)
    @settings(max_examples=100)
    def test_full_name_with_package(self, name: str, package: str) -> None:
        """full_name includes package."""
        service = ServiceDescriptor(name=name, package=package)
        if package:
            assert service.full_name == f"{package}.{name}"
        else:
            assert service.full_name == name

    @given(service_name=names, method_name=names)
    @settings(max_examples=100)
    def test_add_and_get_method(self, service_name: str, method_name: str) -> None:
        """Added method can be retrieved."""
        service = ServiceDescriptor(name=service_name)
        method = MethodDescriptor(name=method_name, method_type=MethodType.UNARY,
                                  input_type="Request", output_type="Response")
        service.add_method(method)
        retrieved = service.get_method(method_name)
        assert retrieved is not None
        assert retrieved.name == method_name

    @given(service_name=names, method_name=names)
    @settings(max_examples=100)
    def test_get_nonexistent_method(self, service_name: str, method_name: str) -> None:
        """Getting nonexistent method returns None."""
        service = ServiceDescriptor(name=service_name)
        assert service.get_method(method_name) is None


class TestGRPCService:
    """Property tests for GRPCService."""

    @given(service_name=names, method_name=names)
    @settings(max_examples=100)
    def test_register_handler(self, service_name: str, method_name: str) -> None:
        """Handler can be registered and retrieved."""
        descriptor = ServiceDescriptor(name=service_name)
        method = MethodDescriptor(name=method_name, method_type=MethodType.UNARY,
                                  input_type="Request", output_type="Response")
        descriptor.add_method(method)
        service: GRPCService[Any] = GRPCService(descriptor)
        handler = lambda req, ctx: "response"
        service.register_handler(method_name, handler)
        assert service.get_handler(method_name) is not None

    @given(service_name=names)
    @settings(max_examples=100)
    def test_name_property(self, service_name: str) -> None:
        """name property returns service name."""
        descriptor = ServiceDescriptor(name=service_name)
        service: GRPCService[Any] = GRPCService(descriptor)
        assert service.name == service_name


class TestServiceRegistry:
    """Property tests for ServiceRegistry."""

    @given(service_name=names)
    @settings(max_examples=100)
    def test_register_and_get(self, service_name: str) -> None:
        """Registered service can be retrieved."""
        registry = ServiceRegistry()
        descriptor = ServiceDescriptor(name=service_name)
        service: GRPCService[Any] = GRPCService(descriptor)
        registry.register(service)
        retrieved = registry.get(service_name)
        assert retrieved is not None

    @given(names_list=st.lists(names, min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_list_services(self, names_list: list[str]) -> None:
        """list_services returns all service names."""
        registry = ServiceRegistry()
        for name in names_list:
            descriptor = ServiceDescriptor(name=name)
            service: GRPCService[Any] = GRPCService(descriptor)
            registry.register(service)
        listed = registry.list_services()
        assert set(listed) == set(names_list)


class TestProtoField:
    """Property tests for ProtoField."""

    @given(name=names, number=field_numbers, field_type=proto_types)
    @settings(max_examples=100)
    def test_to_proto_format(self, name: str, number: int, field_type: str) -> None:
        """to_proto produces valid format."""
        field = ProtoField(name=name, number=number, field_type=field_type)
        proto = field.to_proto()
        assert name in proto
        assert str(number) in proto
        assert field_type in proto

    @given(name=names, number=field_numbers, field_type=proto_types)
    @settings(max_examples=100)
    def test_repeated_field(self, name: str, number: int, field_type: str) -> None:
        """Repeated field has 'repeated' prefix."""
        field = ProtoField(name=name, number=number, field_type=field_type, repeated=True)
        proto = field.to_proto()
        assert "repeated" in proto


class TestProtoMessage:
    """Property tests for ProtoMessage."""

    @given(name=names)
    @settings(max_examples=100)
    def test_to_proto_format(self, name: str) -> None:
        """to_proto produces valid message format."""
        message = ProtoMessage(name=name)
        proto = message.to_proto()
        assert f"message {name}" in proto
        assert "{" in proto
        assert "}" in proto

    @given(msg_name=names, field_name=names, number=field_numbers, field_type=proto_types)
    @settings(max_examples=100)
    def test_add_field(self, msg_name: str, field_name: str, number: int, field_type: str) -> None:
        """Added field appears in proto."""
        message = ProtoMessage(name=msg_name)
        message.add_field(field_name, number, field_type)
        proto = message.to_proto()
        assert field_name in proto


class TestProtoGenerator:
    """Property tests for ProtoGenerator."""

    @given(package=packages)
    @settings(max_examples=100)
    def test_generate_with_package(self, package: str) -> None:
        """Generated proto includes package."""
        generator = ProtoGenerator(package=package)
        proto = generator.generate()
        assert 'syntax = "proto3"' in proto
        if package:
            assert f"package {package}" in proto

    @given(msg_name=names)
    @settings(max_examples=100)
    def test_generate_with_message(self, msg_name: str) -> None:
        """Generated proto includes message."""
        generator = ProtoGenerator()
        message = ProtoMessage(name=msg_name)
        generator.add_message(message)
        proto = generator.generate()
        assert f"message {msg_name}" in proto

    @given(service_name=names, method_name=names)
    @settings(max_examples=100)
    def test_generate_with_service(self, service_name: str, method_name: str) -> None:
        """Generated proto includes service."""
        generator = ProtoGenerator()
        service = ServiceDescriptor(name=service_name)
        method = MethodDescriptor(name=method_name, method_type=MethodType.UNARY,
                                  input_type="Request", output_type="Response")
        service.add_method(method)
        generator.add_service(service)
        proto = generator.generate()
        assert f"service {service_name}" in proto
        assert f"rpc {method_name}" in proto


class TestHelperFunctions:
    """Property tests for helper functions."""

    @given(name=names, package=packages)
    @settings(max_examples=100)
    def test_create_service_descriptor(self, name: str, package: str) -> None:
        """create_service_descriptor creates valid descriptor."""
        descriptor = create_service_descriptor(name, package)
        assert descriptor.name == name
        assert descriptor.package == package

    @given(name=names, input_type=names, output_type=names)
    @settings(max_examples=100)
    def test_create_unary_method(self, name: str, input_type: str, output_type: str) -> None:
        """create_unary_method creates unary method."""
        method = create_unary_method(name, input_type, output_type)
        assert method.name == name
        assert method.method_type == MethodType.UNARY

    @given(name=names, method_type=method_types)
    @settings(max_examples=100)
    def test_create_streaming_method(self, name: str, method_type: MethodType) -> None:
        """create_streaming_method creates correct type."""
        method = create_streaming_method(name, "Request", "Response", method_type)
        assert method.name == name
        assert method.method_type == method_type


# Type hint for Any
from typing import Any
