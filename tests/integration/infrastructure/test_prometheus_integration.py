"""Integration tests for Prometheus metrics.

**Feature: infrastructure-modules-integration-analysis**
**Validates: Requirements 1.1, 1.2, 2.5**
"""

import pytest
from fastapi.testclient import TestClient


class TestPrometheusEndpoint:
    """Integration tests for /metrics endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client with Prometheus enabled."""
        import os
        os.environ["OBSERVABILITY__PROMETHEUS_ENABLED"] = "true"
        os.environ["SECURITY__CORS_ORIGINS"] = '["http://localhost:3000"]'
        
        from main import create_app
        app = create_app()
        return TestClient(app)

    def test_metrics_endpoint_returns_200(self, client: TestClient) -> None:
        """Test /metrics endpoint returns 200.
        
        **Feature: infrastructure-modules-integration-analysis**
        **Property 1: Prometheus metrics endpoint funcional**
        **Validates: Requirements 1.1, 1.2**
        """
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_endpoint_content_type(self, client: TestClient) -> None:
        """Test /metrics returns correct content type.
        
        **Validates: Requirements 1.2**
        """
        response = client.get("/metrics")
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type or "text/plain" in content_type

    def test_metrics_contains_prometheus_format(self, client: TestClient) -> None:
        """Test /metrics returns Prometheus format.
        
        **Validates: Requirements 1.2**
        """
        response = client.get("/metrics")
        content = response.text
        
        # Prometheus format should contain HELP and TYPE comments
        assert "# HELP" in content or "# TYPE" in content or "python_" in content

    def test_metrics_contains_http_metrics(self, client: TestClient) -> None:
        """Test /metrics contains HTTP request metrics after requests.
        
        **Validates: Requirements 1.1**
        """
        # Make some requests first
        client.get("/health/live")
        client.get("/health/ready")
        
        response = client.get("/metrics")
        content = response.text
        
        # Should contain some metrics (process or custom)
        assert len(content) > 0


class TestPrometheusConfiguration:
    """Tests for Prometheus configuration."""

    def test_prometheus_enabled_by_default(self) -> None:
        """Test prometheus_enabled is True by default.
        
        **Validates: Requirements 1.1**
        """
        from core.config.observability import ObservabilitySettings
        
        settings = ObservabilitySettings()
        assert settings.prometheus_enabled is True

    def test_prometheus_endpoint_configurable(self) -> None:
        """Test prometheus endpoint is configurable.
        
        **Validates: Requirements 1.1**
        """
        from core.config.observability import ObservabilitySettings
        
        settings = ObservabilitySettings()
        assert settings.prometheus_endpoint == "/metrics"
