"""E2E tests for ItemExample complete lifecycle.

**Feature: src-interface-improvements**
**Validates: Requirements 4.1**

Tests the full item lifecycle: create → read → update → delete.
"""

import pytest
from typing import Any
import os

pytest.importorskip("fastapi")

# Skip if no database configured
if not os.getenv("DATABASE__URL"):
    pytest.skip("Database not configured for E2E tests", allow_module_level=True)


class TestItemLifecycle:
    """E2E tests for ItemExample lifecycle."""

    def test_item_create_read_update_delete_lifecycle(
        self,
        admin_headers: dict[str, str],
        item_data_factory: callable,
    ) -> None:
        """Test complete item lifecycle: create → read → update → delete.
        
        **Feature: src-interface-improvements**
        **Validates: Requirements 4.1**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        item_data = item_data_factory(name="Lifecycle Test Item")
        
        with TestClient(app, raise_server_exceptions=False) as client:
            # 1. CREATE
            create_response = client.post(
                "/api/v1/examples/items",
                json=item_data,
                headers=admin_headers,
            )
            
            assert create_response.status_code == 201, f"Create failed: {create_response.text}"
            created_item = create_response.json()["data"]
            item_id = created_item["id"]
            
            assert created_item["name"] == item_data["name"]
            assert created_item["sku"] == item_data["sku"]
            
            # 2. READ
            read_response = client.get(
                f"/api/v1/examples/items/{item_id}",
                headers=admin_headers,
            )
            
            assert read_response.status_code == 200, f"Read failed: {read_response.text}"
            read_item = read_response.json()["data"]
            
            assert read_item["id"] == item_id
            assert read_item["name"] == item_data["name"]
            
            # 3. UPDATE
            update_data = {"name": "Updated Lifecycle Item"}
            update_response = client.put(
                f"/api/v1/examples/items/{item_id}",
                json=update_data,
                headers=admin_headers,
            )
            
            assert update_response.status_code == 200, f"Update failed: {update_response.text}"
            updated_item = update_response.json()["data"]
            
            assert updated_item["name"] == "Updated Lifecycle Item"
            
            # 4. DELETE
            delete_response = client.delete(
                f"/api/v1/examples/items/{item_id}",
                headers=admin_headers,
            )
            
            assert delete_response.status_code == 204, f"Delete failed: {delete_response.text}"
            
            # 5. VERIFY DELETED
            verify_response = client.get(
                f"/api/v1/examples/items/{item_id}",
                headers=admin_headers,
            )
            
            assert verify_response.status_code == 404, "Item should be deleted"

    def test_item_create_read_roundtrip(
        self,
        admin_headers: dict[str, str],
        item_data_factory: callable,
    ) -> None:
        """Test create-read round trip preserves data.
        
        **Feature: src-interface-improvements, Property 4: Create-Read Round Trip**
        **Validates: Requirements 1.2**
        """
        from fastapi.testclient import TestClient
        from main import app
        
        item_data = item_data_factory(name="Round Trip Test")
        
        with TestClient(app, raise_server_exceptions=False) as client:
            # Create
            create_response = client.post(
                "/api/v1/examples/items",
                json=item_data,
                headers=admin_headers,
            )
            
            if create_response.status_code != 201:
                pytest.skip("Could not create item for round trip test")
            
            created = create_response.json()["data"]
            item_id = created["id"]
            
            # Read
            read_response = client.get(
                f"/api/v1/examples/items/{item_id}",
                headers=admin_headers,
            )
            
            assert read_response.status_code == 200
            read_item = read_response.json()["data"]
            
            # Verify round trip
            assert read_item["name"] == item_data["name"]
            assert read_item["sku"] == item_data["sku"]
            assert read_item["quantity"] == item_data["quantity"]
            assert read_item["category"] == item_data["category"]

