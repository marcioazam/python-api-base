"""Unit tests for request ID middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from my_app.adapters.api.middleware.request_id import (
    RequestIDMiddleware,
    get_request_id,
)
from my_app.infrastructure.logging import get_request_id as get_ctx_request_id


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app with request ID middleware."""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/request-id")
    async def get_request_id_endpoint(request):
        return {"request_id": request.state.request_id}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware."""

    def test_generates_request_id_when_not_provided(
        self, client: TestClient
    ) -> None:
        """Test that middleware generates request ID when not in headers."""
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        # Should be a valid UUID format
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID format

    def test_uses_provided_request_id(self, client: TestClient) -> None:
        """Test that middleware uses request ID from headers."""
        custom_id = "custom-request-id-12345"
        response = client.get("/test", headers={"X-Request-ID": custom_id})

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == custom_id

    def test_request_id_in_request_state(self) -> None:
        """Test that request ID is available in request state."""
        from fastapi import FastAPI, Request
        
        test_app = FastAPI()
        test_app.add_middleware(RequestIDMiddleware)
        
        captured_id = None

        @test_app.get("/capture")
        async def capture_endpoint(request: Request):
            nonlocal captured_id
            captured_id = request.state.request_id
            return {"captured": True}

        client = TestClient(test_app)
        response = client.get("/capture")

        assert response.status_code == 200
        assert captured_id is not None
        assert captured_id == response.headers["X-Request-ID"]

    def test_different_requests_get_different_ids(
        self, client: TestClient
    ) -> None:
        """Test that each request gets a unique ID."""
        response1 = client.get("/test")
        response2 = client.get("/test")

        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]

        assert id1 != id2


class TestGetRequestIdHelper:
    """Tests for get_request_id helper function."""

    def test_returns_none_when_no_request_id(self) -> None:
        """Test that helper returns None when no request ID in state."""
        from starlette.requests import Request
        from starlette.testclient import TestClient as StarletteTestClient

        # Create a mock request without request_id
        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)

        result = get_request_id(request)
        assert result is None

    def test_returns_request_id_when_set(self) -> None:
        """Test that helper returns request ID when set in state."""
        from starlette.requests import Request

        scope = {"type": "http", "method": "GET", "path": "/", "state": {}}
        request = Request(scope)
        request.state.request_id = "test-id-123"

        result = get_request_id(request)
        assert result == "test-id-123"
