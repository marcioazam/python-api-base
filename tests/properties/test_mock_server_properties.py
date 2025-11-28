"""Property-based tests for Mock Server.

**Feature: api-architecture-analysis, Task 10.3: Mock Server**
**Validates: Requirements 8.1**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.mock_server import (
    MockDataGenerator,
    MockResponse,
    MockServer,
)


class TestMockServerProperties:
    """Property tests for Mock Server."""

    @settings(max_examples=50)
    @given(
        path=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N"))).map(lambda x: f"/{x}"),
        method=st.sampled_from(["GET", "POST", "PUT", "DELETE"]),
        status_code=st.integers(min_value=200, max_value=599),
    )
    def test_registered_endpoint_returns_configured_status(
        self, path: str, method: str, status_code: int
    ) -> None:
        """
        For any registered endpoint, handle_request SHALL return configured status code.
        """
        server = MockServer()
        server.register(path, method, {"data": "test"}, status_code)
        
        response = server.handle_request(method, path)
        
        assert response.status_code == status_code

    @settings(max_examples=50)
    @given(
        path=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))).map(lambda x: f"/{x}"),
        body=st.dictionaries(
            keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
            values=st.text(min_size=1, max_size=20),
            max_size=3,
        ),
    )
    def test_registered_endpoint_returns_configured_body(self, path: str, body: dict) -> None:
        """
        For any registered endpoint, handle_request SHALL return configured body.
        """
        server = MockServer()
        server.register(path, "GET", body)
        
        response = server.handle_request("GET", path)
        
        assert response.body == body


    @settings(max_examples=30)
    @given(
        num_requests=st.integers(min_value=1, max_value=10),
    )
    def test_all_requests_are_recorded(self, num_requests: int) -> None:
        """
        All requests to mock server SHALL be recorded.
        """
        server = MockServer()
        server.register("/test", "GET", {"ok": True})
        
        for i in range(num_requests):
            server.handle_request("GET", "/test")
        
        recorded = server.get_recorded_requests()
        
        assert len(recorded) == num_requests

    def test_unregistered_endpoint_returns_404(self) -> None:
        """
        Requests to unregistered endpoints SHALL return 404.
        """
        server = MockServer()
        
        response = server.handle_request("GET", "/nonexistent")
        
        assert response.status_code == 404

    @settings(max_examples=30)
    @given(
        responses=st.lists(
            st.tuples(
                st.integers(min_value=200, max_value=299),
                st.dictionaries(
                    keys=st.just("value"),
                    values=st.integers(min_value=0, max_value=100),
                    min_size=1,
                    max_size=1,
                ),
            ),
            min_size=2,
            max_size=5,
        ),
    )
    def test_sequential_responses_cycle_through(self, responses: list) -> None:
        """
        Sequential mode SHALL cycle through configured responses.
        """
        server = MockServer()
        server.register_sequential("/test", "GET", responses)
        
        for i, (expected_status, expected_body) in enumerate(responses):
            response = server.handle_request("GET", "/test")
            assert response.status_code == expected_status
            assert response.body == expected_body

    def test_path_parameter_matching(self) -> None:
        """
        Endpoints with path parameters SHALL match actual paths.
        """
        server = MockServer()
        server.register("/items/{id}", "GET", {"id": "matched"})
        
        response = server.handle_request("GET", "/items/123")
        
        assert response.status_code == 200
        assert response.body == {"id": "matched"}

    def test_callback_mode_invokes_handler(self) -> None:
        """
        Callback mode SHALL invoke the registered handler.
        """
        server = MockServer()
        
        def handler(request):
            return 201, {"received": request.path}
        
        server.register_callback("/callback", "POST", handler)
        
        response = server.handle_request("POST", "/callback")
        
        assert response.status_code == 201
        assert response.body == {"received": "/callback"}

    def test_reset_clears_all_state(self) -> None:
        """
        Reset SHALL clear all endpoints and recorded requests.
        """
        server = MockServer()
        server.register("/test", "GET", {})
        server.handle_request("GET", "/test")
        server.set_state("key", "value")
        
        server.reset()
        
        assert len(server.get_recorded_requests()) == 0
        assert server.get_state("key") is None


class TestMockDataGeneratorProperties:
    """Property tests for MockDataGenerator."""

    @settings(max_examples=30)
    @given(
        min_val=st.integers(min_value=0, max_value=100),
        max_val=st.integers(min_value=101, max_value=1000),
    )
    def test_integer_generation_respects_bounds(self, min_val: int, max_val: int) -> None:
        """
        Generated integers SHALL respect min/max bounds.
        """
        generator = MockDataGenerator(seed=42)
        schema = {"type": "integer", "minimum": min_val, "maximum": max_val}
        
        value = generator.generate(schema)
        
        assert min_val <= value <= max_val

    def test_object_generation_includes_all_properties(self) -> None:
        """
        Generated objects SHALL include all schema properties.
        """
        generator = MockDataGenerator(seed=42)
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"},
            },
        }
        
        value = generator.generate(schema)
        
        assert "name" in value
        assert "age" in value
        assert "active" in value
        assert isinstance(value["name"], str)
        assert isinstance(value["age"], int)
        assert isinstance(value["active"], bool)

    @settings(max_examples=20)
    @given(
        min_items=st.integers(min_value=1, max_value=3),
        max_items=st.integers(min_value=4, max_value=10),
    )
    def test_array_generation_respects_item_count(self, min_items: int, max_items: int) -> None:
        """
        Generated arrays SHALL respect minItems/maxItems.
        """
        generator = MockDataGenerator(seed=42)
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": min_items,
            "maxItems": max_items,
        }
        
        value = generator.generate(schema)
        
        assert min_items <= len(value) <= max_items
