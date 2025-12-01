"""Property-based tests for JSON-RPC support.

**Feature: api-architecture-analysis, Property 3: JSON-RPC support**
**Validates: Requirements 4.5**
"""

import json

import pytest
from hypothesis import given, settings, strategies as st

from my_app.interface.api.jsonrpc import (
    JSONRPCError,
    JSONRPCErrorCode,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCRouter,
    JSONRPCServer,
    MethodDescriptor,
)


identifier_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"),
    min_size=1,
    max_size=20,
)

id_strategy = st.one_of(
    st.integers(min_value=1, max_value=10000),
    st.text(min_size=1, max_size=20),
    st.none(),
)


class TestJSONRPCError:
    """Tests for JSONRPCError."""

    @given(code=st.integers(), message=st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_to_dict_contains_code_and_message(self, code: int, message: str):
        """to_dict should contain code and message."""
        error = JSONRPCError(code=code, message=message)
        result = error.to_dict()
        assert result["code"] == code
        assert result["message"] == message

    @given(data=st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_to_dict_includes_data_when_present(self, data: str):
        """to_dict should include data when present."""
        error = JSONRPCError(code=-32600, message="Error", data=data)
        result = error.to_dict()
        assert result["data"] == data

    def test_parse_error_has_correct_code(self):
        """parse_error should have correct error code."""
        error = JSONRPCError.parse_error()
        assert error.code == JSONRPCErrorCode.PARSE_ERROR

    def test_method_not_found_includes_method_name(self):
        """method_not_found should include method name."""
        error = JSONRPCError.method_not_found("test_method")
        assert error.code == JSONRPCErrorCode.METHOD_NOT_FOUND
        assert error.data == "test_method"


class TestJSONRPCRequest:
    """Tests for JSONRPCRequest."""

    @given(method=identifier_strategy, id=id_strategy)
    @settings(max_examples=50)
    def test_to_dict_contains_method(self, method: str, id: str | int | None):
        """to_dict should contain method."""
        request = JSONRPCRequest(method=method, id=id)
        result = request.to_dict()
        assert result["method"] == method
        assert result["jsonrpc"] == "2.0"

    @given(method=identifier_strategy)
    @settings(max_examples=50)
    def test_is_notification_when_no_id(self, method: str):
        """is_notification should be True when no id."""
        request = JSONRPCRequest(method=method, id=None)
        assert request.is_notification is True

    @given(method=identifier_strategy, id=st.integers(min_value=1))
    @settings(max_examples=50)
    def test_is_not_notification_when_has_id(self, method: str, id: int):
        """is_notification should be False when has id."""
        request = JSONRPCRequest(method=method, id=id)
        assert request.is_notification is False

    @given(method=identifier_strategy)
    @settings(max_examples=50)
    def test_to_json_is_valid_json(self, method: str):
        """to_json should produce valid JSON."""
        request = JSONRPCRequest(method=method, id=1)
        json_str = request.to_json()
        parsed = json.loads(json_str)
        assert parsed["method"] == method

    @given(method=identifier_strategy)
    @settings(max_examples=50)
    def test_from_dict_round_trip(self, method: str):
        """from_dict should create equivalent request."""
        original = JSONRPCRequest(method=method, id=1, params={"a": 1})
        data = original.to_dict()
        restored = JSONRPCRequest.from_dict(data)
        assert restored.method == original.method
        assert restored.id == original.id
        assert restored.params == original.params


class TestJSONRPCResponse:
    """Tests for JSONRPCResponse."""

    @given(id=id_strategy, result=st.text(max_size=50))
    @settings(max_examples=50)
    def test_success_response_has_result(self, id: str | int | None, result: str):
        """Success response should have result."""
        response = JSONRPCResponse.success(id=id, result=result)
        assert response.result == result
        assert response.error is None
        assert response.is_error is False

    @given(id=id_strategy)
    @settings(max_examples=50)
    def test_failure_response_has_error(self, id: str | int | None):
        """Failure response should have error."""
        error = JSONRPCError.internal_error()
        response = JSONRPCResponse.failure(id=id, error=error)
        assert response.error is error
        assert response.is_error is True

    @given(id=st.integers(min_value=1), result=st.text(max_size=50))
    @settings(max_examples=50)
    def test_to_json_is_valid_json(self, id: int, result: str):
        """to_json should produce valid JSON."""
        response = JSONRPCResponse.success(id=id, result=result)
        json_str = response.to_json()
        parsed = json.loads(json_str)
        assert parsed["result"] == result


class TestMethodDescriptor:
    """Tests for MethodDescriptor."""

    @given(name=identifier_strategy, description=st.text(max_size=100) | st.none())
    @settings(max_examples=50)
    def test_to_dict_contains_name(self, name: str, description: str | None):
        """to_dict should contain name."""

        async def handler():
            pass

        descriptor = MethodDescriptor(
            name=name, handler=handler, description=description
        )
        result = descriptor.to_dict()
        assert result["name"] == name


class TestJSONRPCRouter:
    """Tests for JSONRPCRouter."""

    @given(prefix=identifier_strategy, method_name=identifier_strategy)
    @settings(max_examples=50)
    def test_method_decorator_registers_method(self, prefix: str, method_name: str):
        """method decorator should register the method."""
        router = JSONRPCRouter(prefix=prefix)

        @router.method(name=method_name)
        async def test_handler():
            return "result"

        full_name = f"{prefix}.{method_name}"
        assert full_name in router.list_methods()

    @given(method_name=identifier_strategy)
    @settings(max_examples=50)
    def test_get_method_returns_descriptor(self, method_name: str):
        """get_method should return the method descriptor."""
        router = JSONRPCRouter()

        @router.method(name=method_name)
        async def test_handler():
            return "result"

        descriptor = router.get_method(method_name)
        assert descriptor is not None
        assert descriptor.name == method_name

    @given(method_name=identifier_strategy)
    @settings(max_examples=50)
    def test_get_nonexistent_method_returns_none(self, method_name: str):
        """get_method should return None for nonexistent method."""
        router = JSONRPCRouter()
        assert router.get_method(method_name) is None

    @pytest.mark.asyncio
    async def test_call_method_with_params(self):
        """call should invoke method with params."""
        router = JSONRPCRouter()

        @router.method(name="add")
        async def add(a: int, b: int) -> int:
            return a + b

        result = await router.call("add", {"a": 2, "b": 3})
        assert result == 5


class TestJSONRPCServer:
    """Tests for JSONRPCServer."""

    def test_include_router_adds_methods(self):
        """include_router should add router's methods."""
        server = JSONRPCServer()
        router = JSONRPCRouter()

        @router.method(name="test")
        async def test_handler():
            return "result"

        server.include_router(router)
        assert "test" in server.list_methods()

    @pytest.mark.asyncio
    async def test_handle_request_success(self):
        """handle_request should return success response."""
        server = JSONRPCServer()

        async def echo(message: str) -> str:
            return message

        server.register_method("echo", echo)
        request = JSONRPCRequest(method="echo", params={"message": "hello"}, id=1)
        response = await server.handle_request(request)
        assert response is not None
        assert response.result == "hello"
        assert response.is_error is False

    @pytest.mark.asyncio
    async def test_handle_request_method_not_found(self):
        """handle_request should return error for unknown method."""
        server = JSONRPCServer()
        request = JSONRPCRequest(method="unknown", id=1)
        response = await server.handle_request(request)
        assert response is not None
        assert response.is_error is True
        assert response.error is not None
        assert response.error.code == JSONRPCErrorCode.METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_handle_notification_returns_none(self):
        """handle_request should return None for notifications."""
        server = JSONRPCServer()

        async def noop():
            pass

        server.register_method("noop", noop)
        request = JSONRPCRequest(method="noop", id=None)
        response = await server.handle_request(request)
        assert response is None

    @pytest.mark.asyncio
    async def test_handle_json_valid_request(self):
        """handle_json should process valid JSON request."""
        server = JSONRPCServer()

        async def add(a: int, b: int) -> int:
            return a + b

        server.register_method("add", add)
        json_request = '{"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1}'
        json_response = await server.handle_json(json_request)
        response = json.loads(json_response)
        assert response["result"] == 3

    @pytest.mark.asyncio
    async def test_handle_json_parse_error(self):
        """handle_json should return parse error for invalid JSON."""
        server = JSONRPCServer()
        json_response = await server.handle_json("invalid json")
        response = json.loads(json_response)
        assert response["error"]["code"] == JSONRPCErrorCode.PARSE_ERROR

    @pytest.mark.asyncio
    async def test_handle_batch_requests(self):
        """handle_batch should process multiple requests."""
        server = JSONRPCServer()

        async def double(n: int) -> int:
            return n * 2

        server.register_method("double", double)
        requests = [
            JSONRPCRequest(method="double", params={"n": 1}, id=1),
            JSONRPCRequest(method="double", params={"n": 2}, id=2),
        ]
        responses = await server.handle_batch(requests)
        assert len(responses) == 2
        assert responses[0].result == 2
        assert responses[1].result == 4
