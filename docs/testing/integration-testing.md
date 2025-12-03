# Integration Testing

## Overview

Testes de integração verificam a interação entre componentes, incluindo banco de dados e APIs.

## Database Setup

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost:5432/test_db",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async with AsyncSession(db_engine) as session:
        yield session
        await session.rollback()
```

## Repository Tests

```python
@pytest.mark.asyncio
async def test_create_and_get_user(db_session):
    repository = UserRepository(db_session)
    
    user = User(id="user-123", email="test@example.com", name="Test")
    created = await repository.create(user)
    
    assert created.id == "user-123"
    
    retrieved = await repository.get("user-123")
    assert retrieved is not None
    assert retrieved.email == "test@example.com"

@pytest.mark.asyncio
async def test_find_by_specification(db_session):
    repository = UserRepository(db_session)
    
    # Create test data
    await repository.create(User(id="1", email="active@test.com", name="Active", is_active=True))
    await repository.create(User(id="2", email="inactive@test.com", name="Inactive", is_active=False))
    
    # Query with specification
    spec = equals("is_active", True)
    users = await repository.find_by_spec(spec)
    
    assert len(users) == 1
    assert users[0].email == "active@test.com"
```

## API Tests

```python
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "name": "Test", "password": "password123"},
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    response = await client.get("/api/v1/users/nonexistent")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient):
    # Create first user
    await client.post("/api/v1/users", json={"email": "dup@test.com", "name": "First", "password": "pass123"})
    
    # Try to create duplicate
    response = await client.post("/api/v1/users", json={"email": "dup@test.com", "name": "Second", "password": "pass123"})
    
    assert response.status_code == 400
```

## Cache Tests

```python
@pytest.mark.asyncio
async def test_cache_hit(redis_client):
    cache = RedisCacheProvider(redis_client)
    
    await cache.set("key", {"data": "value"}, ttl=60)
    result = await cache.get("key")
    
    assert result == {"data": "value"}

@pytest.mark.asyncio
async def test_cache_expiration(redis_client):
    cache = RedisCacheProvider(redis_client)
    
    await cache.set("key", "value", ttl=1)
    await asyncio.sleep(1.5)
    
    result = await cache.get("key")
    assert result is None
```

## Test Isolation

```python
@pytest.fixture(autouse=True)
async def clean_database(db_session):
    """Clean database before each test."""
    yield
    # Rollback happens automatically in db_session fixture

@pytest.fixture(autouse=True)
async def clean_cache(redis_client):
    """Clean cache before each test."""
    await redis_client.flushdb()
    yield
```

## Best Practices

1. **Use fixtures** - For setup and teardown
2. **Isolate tests** - Each test should be independent
3. **Use transactions** - Rollback after each test
4. **Test real interactions** - Don't mock everything
5. **Use testcontainers** - For consistent environments
