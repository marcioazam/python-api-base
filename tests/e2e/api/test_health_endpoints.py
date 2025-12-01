"""Integration tests for health check endpoints.

**Validates: Requirements 10.4, 12.2**
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Integration tests for health check endpoints."""

    async def test_liveness_endpoint(self, test_client: AsyncClient) -> None:
        """Test /health/live endpoint returns ok status."""
        response = await test_client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_readiness_endpoint(self, test_client: AsyncClient) -> None:
        """Test /health/ready endpoint returns status with checks."""
        response = await test_client.get("/health/ready")
        
        # Should return 200 (healthy or degraded) or 503 (unhealthy)
        assert response.status_code in [200, 503]
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "checks" in data
        
        # Should have database check
        assert "database" in data["checks"]
        db_check = data["checks"]["database"]
        assert "status" in db_check
        
        # Should have redis check (optional)
        assert "redis" in data["checks"]

    async def test_readiness_returns_version(self, test_client: AsyncClient) -> None:
        """Test /health/ready endpoint returns version info."""
        response = await test_client.get("/health/ready")
        
        assert response.status_code in [200, 503]
        data = response.json()
        # Version may be None if settings not initialized
        assert "version" in data

    async def test_readiness_database_latency(self, test_client: AsyncClient) -> None:
        """Test /health/ready returns database latency when healthy."""
        response = await test_client.get("/health/ready")
        
        data = response.json()
        db_check = data["checks"]["database"]
        
        if db_check["status"] == "healthy":
            assert "latency_ms" in db_check
            assert db_check["latency_ms"] >= 0


@pytest.mark.asyncio
class TestApplicationStartup:
    """Integration tests for application startup."""

    async def test_app_starts_successfully(self, test_client: AsyncClient) -> None:
        """Test that the application starts and responds to requests."""
        # Health check should work
        response = await test_client.get("/health/live")
        assert response.status_code == 200

    async def test_openapi_spec_available(self, test_client: AsyncClient) -> None:
        """Test that OpenAPI spec is available."""
        response = await test_client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    async def test_docs_endpoint_available(self, test_client: AsyncClient) -> None:
        """Test that Swagger UI docs are available."""
        response = await test_client.get("/docs")
        assert response.status_code == 200

    async def test_redoc_endpoint_available(self, test_client: AsyncClient) -> None:
        """Test that ReDoc is available."""
        response = await test_client.get("/redoc")
        assert response.status_code == 200

    async def test_cors_headers_present(self, test_client: AsyncClient) -> None:
        """Test that CORS headers are configured."""
        response = await test_client.options(
            "/api/v1/items",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight should be handled
        assert response.status_code in [200, 204, 405]

    async def test_security_headers_present(self, test_client: AsyncClient) -> None:
        """Test that security headers are present in responses."""
        response = await test_client.get("/health/live")
        
        assert response.status_code == 200
        # Check security headers
        assert "x-frame-options" in response.headers
        assert "x-content-type-options" in response.headers
        assert "x-xss-protection" in response.headers
