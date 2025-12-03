# End-to-End Testing

## Overview

Testes E2E verificam fluxos completos do sistema, simulando interações reais de usuários.

## Setup

```python
# tests/e2e/conftest.py
import pytest
from httpx import AsyncClient

@pytest.fixture(scope="module")
async def app():
    """Create application with test configuration."""
    from src.main import create_app
    app = create_app(testing=True)
    yield app

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def auth_client(client):
    """Client with authentication."""
    # Login
    response = await client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123",
    })
    token = response.json()["access_token"]
    
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
```

## User Lifecycle Test

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_user_lifecycle(client: AsyncClient):
    """Test complete user lifecycle: create, read, update, delete."""
    
    # 1. Create user
    create_response = await client.post("/api/v1/users", json={
        "email": "lifecycle@test.com",
        "name": "Lifecycle Test",
        "password": "password123",
    })
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]
    
    # 2. Read user
    get_response = await client.get(f"/api/v1/users/{user_id}")
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "lifecycle@test.com"
    
    # 3. Update user
    update_response = await client.patch(f"/api/v1/users/{user_id}", json={
        "name": "Updated Name",
    })
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Name"
    
    # 4. Delete user
    delete_response = await client.delete(f"/api/v1/users/{user_id}")
    assert delete_response.status_code == 204
    
    # 5. Verify deleted
    verify_response = await client.get(f"/api/v1/users/{user_id}")
    assert verify_response.status_code == 404
```

## Order Flow Test

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_order_flow(auth_client: AsyncClient):
    """Test complete order flow: create, add items, confirm, pay."""
    
    # 1. Create order
    order_response = await auth_client.post("/api/v1/orders")
    assert order_response.status_code == 201
    order_id = order_response.json()["id"]
    
    # 2. Add items
    await auth_client.post(f"/api/v1/orders/{order_id}/items", json={
        "product_id": "prod-1",
        "quantity": 2,
    })
    await auth_client.post(f"/api/v1/orders/{order_id}/items", json={
        "product_id": "prod-2",
        "quantity": 1,
    })
    
    # 3. Confirm order
    confirm_response = await auth_client.post(f"/api/v1/orders/{order_id}/confirm")
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"
    
    # 4. Process payment
    payment_response = await auth_client.post(f"/api/v1/orders/{order_id}/pay", json={
        "method": "credit_card",
        "card_token": "tok_test",
    })
    assert payment_response.status_code == 200
    assert payment_response.json()["status"] == "paid"
```

## Authentication Flow Test

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_auth_flow(client: AsyncClient):
    """Test authentication flow: register, login, refresh, logout."""
    
    # 1. Register
    register_response = await client.post("/auth/register", json={
        "email": "auth@test.com",
        "name": "Auth Test",
        "password": "password123",
    })
    assert register_response.status_code == 201
    
    # 2. Login
    login_response = await client.post("/auth/login", json={
        "email": "auth@test.com",
        "password": "password123",
    })
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    
    # 3. Access protected resource
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    me_response = await client.get("/auth/me")
    assert me_response.status_code == 200
    
    # 4. Refresh token
    refresh_response = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert refresh_response.status_code == 200
    
    # 5. Logout
    logout_response = await client.post("/auth/logout")
    assert logout_response.status_code == 200
```

## Running E2E Tests

```bash
# Run all e2e tests
pytest tests/e2e/ -v

# Run with markers
pytest -m e2e

# Run specific flow
pytest tests/e2e/test_user_lifecycle.py -v
```

## Best Practices

1. **Test complete flows** - Not individual endpoints
2. **Use realistic data** - Simulate real usage
3. **Clean up after tests** - Don't leave test data
4. **Run in isolation** - Separate test database
5. **Keep tests independent** - No shared state
