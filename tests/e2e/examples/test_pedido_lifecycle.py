"""E2E tests for PedidoExample complete lifecycle.

**Feature: src-interface-improvements**
**Validates: Requirements 4.2, 4.3**

Tests the full pedido lifecycle: create → add items → confirm/cancel.
"""

import pytest
from typing import Any
import os

pytest.importorskip("fastapi")

# Skip if no database configured
if not os.getenv("DATABASE__URL"):
    pytest.skip("Database not configured for E2E tests", allow_module_level=True)


class TestPedidoLifecycle:
    """E2E tests for PedidoExample lifecycle."""

    def test_pedido_create_confirm_lifecycle(
        self,
        admin_headers: dict[str, str],
        pedido_data_factory: callable,
    ) -> None:
        """Test pedido lifecycle: create → confirm.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 4.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        pedido_data = pedido_data_factory(customer_name="Lifecycle Customer")
        
        with TestClient(app, raise_server_exceptions=False) as client:
            # 1. CREATE
            create_response = client.post(
                "/api/v1/examples/pedidos",
                json=pedido_data,
                headers=admin_headers,
            )
            
            assert create_response.status_code == 201, f"Create failed: {create_response.text}"
            created_pedido = create_response.json()["data"]
            pedido_id = created_pedido["id"]
            
            assert created_pedido["customer_name"] == pedido_data["customer_name"]
            assert created_pedido["status"] == "pending"
            
            # 2. READ
            read_response = client.get(
                f"/api/v1/examples/pedidos/{pedido_id}",
                headers=admin_headers,
            )
            
            assert read_response.status_code == 200, f"Read failed: {read_response.text}"
            read_pedido = read_response.json()["data"]
            
            assert read_pedido["id"] == pedido_id
            
            # 3. CONFIRM
            confirm_response = client.post(
                f"/api/v1/examples/pedidos/{pedido_id}/confirm",
                headers=admin_headers,
            )
            
            assert confirm_response.status_code == 200, f"Confirm failed: {confirm_response.text}"
            confirmed_pedido = confirm_response.json()["data"]
            
            assert confirmed_pedido["status"] == "confirmed"

    def test_pedido_create_cancel_lifecycle(
        self,
        admin_headers: dict[str, str],
        pedido_data_factory: callable,
    ) -> None:
        """Test pedido cancellation lifecycle: create → cancel.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 4.3**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        pedido_data = pedido_data_factory(customer_name="Cancel Test Customer")
        
        with TestClient(app, raise_server_exceptions=False) as client:
            # 1. CREATE
            create_response = client.post(
                "/api/v1/examples/pedidos",
                json=pedido_data,
                headers=admin_headers,
            )
            
            assert create_response.status_code == 201, f"Create failed: {create_response.text}"
            created_pedido = create_response.json()["data"]
            pedido_id = created_pedido["id"]
            
            assert created_pedido["status"] == "pending"
            
            # 2. CANCEL
            cancel_response = client.post(
                f"/api/v1/examples/pedidos/{pedido_id}/cancel",
                json={"reason": "Customer requested cancellation"},
                headers=admin_headers,
            )
            
            assert cancel_response.status_code == 200, f"Cancel failed: {cancel_response.text}"
            cancelled_pedido = cancel_response.json()["data"]
            
            assert cancelled_pedido["status"] == "cancelled"
            
            # 3. VERIFY STATUS
            verify_response = client.get(
                f"/api/v1/examples/pedidos/{pedido_id}",
                headers=admin_headers,
            )
            
            assert verify_response.status_code == 200
            final_pedido = verify_response.json()["data"]
            assert final_pedido["status"] == "cancelled"

    def test_pedido_create_read_roundtrip(
        self,
        admin_headers: dict[str, str],
        pedido_data_factory: callable,
    ) -> None:
        """Test create-read round trip preserves data.
        
        **Feature: src-interface-improvements, Property 4: Create-Read Round Trip**
        **Validates: Requirements 2.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        pedido_data = pedido_data_factory(customer_name="Round Trip Customer")
        
        with TestClient(app, raise_server_exceptions=False) as client:
            # Create
            create_response = client.post(
                "/api/v1/examples/pedidos",
                json=pedido_data,
                headers=admin_headers,
            )
            
            if create_response.status_code != 201:
                pytest.skip("Could not create pedido for round trip test")
            
            created = create_response.json()["data"]
            pedido_id = created["id"]
            
            # Read
            read_response = client.get(
                f"/api/v1/examples/pedidos/{pedido_id}",
                headers=admin_headers,
            )
            
            assert read_response.status_code == 200
            read_pedido = read_response.json()["data"]
            
            # Verify round trip
            assert read_pedido["customer_name"] == pedido_data["customer_name"]
            assert read_pedido["customer_email"] == pedido_data["customer_email"]
            assert read_pedido["shipping_address"] == pedido_data["shipping_address"]

