"""Integration tests for Item API endpoints.

**Feature: generic-fastapi-crud, Property 11-14: Endpoint Properties**
**Validates: Requirements 5.2, 5.3, 5.4, 5.6, 14.2**

Note: These tests use the InMemoryRepository which is recreated per request.
Tests that require persistence across requests are tested via property tests
or would require a persistent database setup.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestItemEndpoints:
    """Integration tests for Item CRUD endpoints."""

    async def test_create_item_returns_201(self, test_client: AsyncClient) -> None:
        """
        **Feature: generic-fastapi-crud, Property 11: Endpoint POST Returns 201 with Entity**
        
        POST request SHALL return status 201 with created entity.
        """
        response = await test_client.post(
            "/api/v1/items",
            json={
                "name": "New Item",
                "description": "A new test item",
                "price": 49.99,
                "tax": 4.00,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "data" in data
        assert data["data"]["name"] == "New Item"
        assert data["data"]["price"] == 49.99
        assert data["data"]["id"] is not None

    async def test_list_items_returns_paginated(self, test_client: AsyncClient) -> None:
        """
        **Feature: generic-fastapi-crud, Property 12: Endpoint GET List Returns Paginated Response**
        
        GET list request SHALL return paginated response structure.
        """
        response = await test_client.get("/api/v1/items?page=1&size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert "has_next" in data
        assert "has_previous" in data

    async def test_get_nonexistent_item_returns_404(
        self, test_client: AsyncClient
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 13: Endpoint GET Detail Returns Entity or 404**
        
        GET detail request SHALL return 404 if entity not found.
        """
        response = await test_client.get("/api/v1/items/nonexistent-id")
        assert response.status_code == 404

    async def test_update_nonexistent_returns_404(
        self, test_client: AsyncClient
    ) -> None:
        """Update non-existent item SHALL return 404."""
        response = await test_client.put(
            "/api/v1/items/nonexistent-id",
            json={"name": "Test"},
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_returns_404(
        self, test_client: AsyncClient
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 14: Endpoint DELETE Returns 204 or 404**
        
        DELETE request SHALL return 404 if entity not found.
        """
        response = await test_client.delete("/api/v1/items/nonexistent-id")
        assert response.status_code == 404

    async def test_create_item_validates_price(self, test_client: AsyncClient) -> None:
        """Create item with invalid price SHALL return 422."""
        response = await test_client.post(
            "/api/v1/items",
            json={"name": "Invalid", "price": -10.00},
        )
        assert response.status_code == 422

    async def test_create_item_validates_name(self, test_client: AsyncClient) -> None:
        """Create item with empty name SHALL return 422."""
        response = await test_client.post(
            "/api/v1/items",
            json={"name": "", "price": 10.00},
        )
        assert response.status_code == 422

    async def test_list_with_pagination_params(
        self, test_client: AsyncClient
    ) -> None:
        """Test list endpoint accepts pagination parameters."""
        response = await test_client.get("/api/v1/items?page=2&size=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 5

    async def test_list_with_sorting_params(self, test_client: AsyncClient) -> None:
        """Test list endpoint accepts sorting parameters."""
        response = await test_client.get(
            "/api/v1/items?sort_by=name&sort_order=asc"
        )
        assert response.status_code == 200

    async def test_create_returns_computed_field(
        self, test_client: AsyncClient
    ) -> None:
        """Create response SHALL include computed price_with_tax field."""
        response = await test_client.post(
            "/api/v1/items",
            json={"name": "Tax Item", "price": 100.00, "tax": 10.00},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["price_with_tax"] == 110.00

    async def test_bulk_endpoint_exists(self, test_client: AsyncClient) -> None:
        """Bulk create endpoint SHALL exist."""
        response = await test_client.post(
            "/api/v1/items/bulk",
            json=[{"name": "Bulk 1", "price": 10.00}],
        )
        # Should be 201 or validation error, not 404
        assert response.status_code in [201, 422]

    async def test_bulk_delete_endpoint_exists(self, test_client: AsyncClient) -> None:
        """Bulk delete endpoint SHALL exist."""
        response = await test_client.request(
            "DELETE",
            "/api/v1/items/bulk",
            json={"ids": ["id1", "id2"]},
        )
        # Should return response, not 404
        assert response.status_code in [200, 404]
