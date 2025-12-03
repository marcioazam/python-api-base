"""Real HTTP integration tests for ItemExample API.

**Feature: src-interface-improvements**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

Tests the full HTTP request/response cycle for ItemExample endpoints
using TestClient with real middleware execution.
"""

import pytest
from typing import Any
import os

pytest.importorskip("fastapi")

# Skip if no database configured
if not os.getenv("DATABASE__URL"):
    pytest.skip("Database not configured for E2E tests", allow_module_level=True)


class TestItemsHTTPReal:
    """Real HTTP tests for ItemExample endpoints."""

    def test_get_items_returns_200_with_pagination(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test GET /api/v1/examples/items returns paginated response.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 1.1**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "size" in data
            assert isinstance(data["items"], list)

    def test_get_items_includes_security_headers(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test GET /api/v1/examples/items includes security headers.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            assert response.status_code == 200
            assert "x-frame-options" in response.headers
            assert "x-content-type-options" in response.headers

    def test_post_item_with_admin_returns_201(
        self,
        admin_headers: dict[str, str],
        item_data_factory: callable,
    ) -> None:
        """Test POST /api/v1/examples/items with admin role creates item.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 1.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        item_data = item_data_factory()
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/examples/items",
                json=item_data,
                headers=admin_headers,
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "data" in data
            assert data["data"]["name"] == item_data["name"]
            assert data["data"]["sku"] == item_data["sku"]

    def test_post_item_without_permission_returns_403(
        self,
        viewer_headers: dict[str, str],
        item_data_factory: callable,
    ) -> None:
        """Test POST /api/v1/examples/items without WRITE permission returns 403.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 1.3**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        item_data = item_data_factory()
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/examples/items",
                json=item_data,
                headers=viewer_headers,
            )
            
            assert response.status_code == 403
            data = response.json()
            assert "detail" in data

    def test_get_item_not_found_returns_404(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test GET /api/v1/examples/items/{id} for non-existent item returns 404.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 1.4**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/v1/examples/items/non-existent-id-12345",
                headers=admin_headers,
            )
            
            assert response.status_code == 404

    def test_delete_item_without_permission_returns_403(
        self,
        viewer_headers: dict[str, str],
    ) -> None:
        """Test DELETE /api/v1/examples/items/{id} without DELETE permission returns 403.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 1.5**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.delete(
                "/api/v1/examples/items/any-item-id",
                headers=viewer_headers,
            )
            
            assert response.status_code == 403

    def test_response_includes_request_id_header(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test all responses include X-Request-ID header.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 3.1**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/items", headers=admin_headers)
            
            assert "x-request-id" in response.headers
            request_id = response.headers["x-request-id"]
            assert len(request_id) > 0

