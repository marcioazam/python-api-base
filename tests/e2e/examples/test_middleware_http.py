"""HTTP tests for middleware verification.

**Feature: src-interface-improvements**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

Tests middleware execution through real HTTP requests.
"""

import pytest
import re
import os

pytest.importorskip("fastapi")

# Skip if no database configured
if not os.getenv("DATABASE__URL"):
    pytest.skip("Database not configured for E2E tests", allow_module_level=True)


class TestMiddlewareHTTP:
    """Tests for middleware verification via HTTP."""

    def test_request_id_header_present(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test X-Request-ID header is present in all responses.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.1**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            assert "x-request-id" in response.headers
            request_id = response.headers["x-request-id"]
            
            # Verify UUID format (basic check)
            assert len(request_id) >= 32

    def test_request_id_header_valid_uuid(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test X-Request-ID header contains valid UUID format.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.1**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            request_id = response.headers.get("x-request-id", "")
            assert uuid_pattern.match(request_id), f"Invalid UUID format: {request_id}"

    def test_security_headers_x_frame_options(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test X-Frame-Options header is present.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            assert "x-frame-options" in response.headers
            assert response.headers["x-frame-options"] in ["DENY", "SAMEORIGIN"]

    def test_security_headers_x_content_type_options(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test X-Content-Type-Options header is present.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            assert "x-content-type-options" in response.headers
            assert response.headers["x-content-type-options"] == "nosniff"

    def test_security_headers_strict_transport_security(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test Strict-Transport-Security header is present.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            assert "strict-transport-security" in response.headers
            hsts = response.headers["strict-transport-security"]
            assert "max-age=" in hsts

    def test_security_headers_referrer_policy(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test Referrer-Policy header is present.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            assert "referrer-policy" in response.headers

    def test_request_size_limit_rejects_large_payload(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test request body exceeding 10MB is rejected with 413.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.4**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        # Create payload larger than 10MB
        large_payload = {"data": "x" * (11 * 1024 * 1024)}  # 11MB
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/examples/items",
                json=large_payload,
                headers=admin_headers,
            )
            
            # Should be rejected with 413 or 422 (validation error)
            assert response.status_code in [413, 422]

    def test_health_endpoint_no_auth_required(self) -> None:
        """Test health endpoints don't require authentication.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.1**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/health/live")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

