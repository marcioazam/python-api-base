"""Real HTTP integration tests for PedidoExample API.

**Feature: src-interface-improvements**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

Tests the full HTTP request/response cycle for PedidoExample endpoints
using TestClient with real middleware execution.
"""

import pytest
from typing import Any
import os

pytest.importorskip("fastapi")

# Skip if no database configured
if not os.getenv("DATABASE__URL"):
    pytest.skip("Database not configured for E2E tests", allow_module_level=True)


class TestPedidosHTTPReal:
    """Real HTTP tests for PedidoExample endpoints."""

    def test_get_pedidos_returns_200_with_pagination(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test GET /api/v1/examples/pedidos returns paginated response.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 2.1**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/examples/pedidos", headers=admin_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "size" in data
            assert isinstance(data["items"], list)

    def test_post_pedido_with_admin_returns_201(
        self,
        admin_headers: dict[str, str],
        pedido_data_factory: callable,
    ) -> None:
        """Test POST /api/v1/examples/pedidos with admin role creates pedido.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 2.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        pedido_data = pedido_data_factory()
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/examples/pedidos",
                json=pedido_data,
                headers=admin_headers,
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "data" in data
            assert data["data"]["customer_name"] == pedido_data["customer_name"]

    def test_confirm_pedido_returns_200(
        self,
        admin_headers: dict[str, str],
        pedido_data_factory: callable,
    ) -> None:
        """Test POST /api/v1/examples/pedidos/{id}/confirm confirms order.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 2.3**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        pedido_data = pedido_data_factory()
        
        with TestClient(app, raise_server_exceptions=False) as client:
            # Create pedido first
            create_response = client.post(
                "/api/v1/examples/pedidos",
                json=pedido_data,
                headers=admin_headers,
            )
            
            if create_response.status_code != 201:
                pytest.skip("Could not create pedido for confirmation test")
            
            pedido_id = create_response.json()["data"]["id"]
            
            # Confirm pedido
            confirm_response = client.post(
                f"/api/v1/examples/pedidos/{pedido_id}/confirm",
                headers=admin_headers,
            )
            
            assert confirm_response.status_code == 200
            data = confirm_response.json()
            assert data["data"]["status"] == "confirmed"

    def test_cancel_pedido_returns_200(
        self,
        admin_headers: dict[str, str],
        pedido_data_factory: callable,
    ) -> None:
        """Test POST /api/v1/examples/pedidos/{id}/cancel cancels order.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 2.4**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        pedido_data = pedido_data_factory()
        
        with TestClient(app, raise_server_exceptions=False) as client:
            # Create pedido first
            create_response = client.post(
                "/api/v1/examples/pedidos",
                json=pedido_data,
                headers=admin_headers,
            )
            
            if create_response.status_code != 201:
                pytest.skip("Could not create pedido for cancellation test")
            
            pedido_id = create_response.json()["data"]["id"]
            
            # Cancel pedido
            cancel_response = client.post(
                f"/api/v1/examples/pedidos/{pedido_id}/cancel",
                json={"reason": "Test cancellation"},
                headers=admin_headers,
            )
            
            assert cancel_response.status_code == 200
            data = cancel_response.json()
            assert data["data"]["status"] == "cancelled"

    def test_pedidos_filtered_by_tenant(
        self,
        admin_headers: dict[str, str],
        tenant_headers: dict[str, str],
    ) -> None:
        """Test GET /api/v1/examples/pedidos filters by X-Tenant-Id.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 2.5**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            # Get pedidos with specific tenant
            response = client.get(
                "/api/v1/examples/pedidos",
                headers=tenant_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # All returned pedidos should belong to the tenant
            tenant_id = tenant_headers["X-Tenant-Id"]
            for pedido in data["items"]:
                if pedido.get("tenant_id"):
                    assert pedido["tenant_id"] == tenant_id

    def test_get_pedido_not_found_returns_404(
        self,
        admin_headers: dict[str, str],
    ) -> None:
        """Test GET /api/v1/examples/pedidos/{id} for non-existent pedido returns 404.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 2.1**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/v1/examples/pedidos/non-existent-id-12345",
                headers=admin_headers,
            )
            
            assert response.status_code == 404

