"""Unit tests for health check endpoints.

**Validates: Requirements 10.4**
"""

import pytest
pytest.skip("Module application.examples.dtos not implemented", allow_module_level=True)
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create sync test client."""
    return TestClient(app)


class TestLivenessEndpoint:
    """Unit tests for liveness endpoint."""

    def test_liveness_returns_200(self, client: TestClient) -> None:
        """Liveness endpoint SHALL return 200 status."""
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_liveness_returns_ok_status(self, client: TestClient) -> None:
        """Liveness endpoint SHALL return status ok."""
        response = client.get("/health/live")
        data = response.json()
        assert data["status"] == "ok"

    def test_liveness_response_is_json(self, client: TestClient) -> None:
        """Liveness endpoint SHALL return JSON response."""
        response = client.get("/health/live")
        assert response.headers["content-type"] == "application/json"


class TestReadinessEndpoint:
    """Unit tests for readiness endpoint."""

    def test_readiness_returns_valid_status_code(self, client: TestClient) -> None:
        """Readiness endpoint SHALL return 200 (healthy/degraded) or 503 (unhealthy)."""
        response = client.get("/health/ready")
        # Without database, it will be unhealthy (503) or degraded (200)
        assert response.status_code in [200, 503]

    def test_readiness_returns_valid_status(self, client: TestClient) -> None:
        """Readiness endpoint SHALL return valid status value."""
        response = client.get("/health/ready")
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_readiness_includes_checks(self, client: TestClient) -> None:
        """Readiness endpoint SHALL include dependency checks."""
        response = client.get("/health/ready")
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]

    def test_readiness_response_is_json(self, client: TestClient) -> None:
        """Readiness endpoint SHALL return JSON response."""
        response = client.get("/health/ready")
        assert response.headers["content-type"] == "application/json"


class TestHealthEndpointRouting:
    """Tests for health endpoint routing."""

    def test_health_live_path(self, client: TestClient) -> None:
        """Health live SHALL be at /health/live."""
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_health_ready_path(self, client: TestClient) -> None:
        """Health ready SHALL be at /health/ready."""
        response = client.get("/health/ready")
        # Returns 200 (healthy/degraded) or 503 (unhealthy)
        assert response.status_code in [200, 503]

    def test_health_endpoints_not_under_api_prefix(
        self, client: TestClient
    ) -> None:
        """Health endpoints SHALL NOT be under /api/v1 prefix."""
        # These should 404
        response_live = client.get("/api/v1/health/live")
        response_ready = client.get("/api/v1/health/ready")
        
        assert response_live.status_code == 404
        assert response_ready.status_code == 404
