# Testing Guide

## Overview

Python API Base uses a comprehensive testing strategy with unit tests, property-based tests, integration tests, and e2e tests.

## Test Structure

```
tests/
├── unit/               # Unit tests
│   ├── core/
│   ├── domain/
│   ├── application/
│   └── infrastructure/
├── integration/        # Integration tests
│   ├── db/
│   ├── cache/
│   └── api/
├── properties/         # Property-based tests
│   └── test_*.py
├── e2e/                # End-to-end tests
├── factories/          # Test data factories
├── fixtures/           # Shared fixtures
└── conftest.py         # Pytest configuration
```

## Unit Testing

### Testing Patterns by Layer

#### Domain Layer

```python
# tests/unit/domain/test_user.py
import pytest
from src.domain.users.aggregates import User
from src.domain.users.events import UserActivatedEvent

class TestUser:
    def test_activate_inactive_user(self):
        user = User(id="123", email="test@example.com", is_active=False)
        
        user.activate()
        
        assert user.is_active is True
        assert len(user._domain_events) == 1
        assert isinstance(user._domain_events[0], UserActivatedEvent)
    
    def test_activate_already_active_user_raises(self):
        user = User(id="123", email="test@example.com", is_active=True)
        
        with pytest.raises(BusinessRuleError):
            user.activate()
```

#### Application Layer - CQRS Handlers

**Command Handlers**

```python
# tests/unit/application/users/commands/test_create_user_handler.py
import pytest
from unittest.mock import AsyncMock, Mock
from application.users.commands import CreateUserHandler, CreateUserCommand

@pytest.fixture
def mock_repository() -> AsyncMock:
    """Mock user repository."""
    repo = AsyncMock()
    repo.exists_by_email = AsyncMock(return_value=False)
    repo.save = AsyncMock()
    return repo

@pytest.fixture
def mock_domain_service() -> Mock:
    """Mock domain service."""
    service = Mock()
    service.validate_email.return_value = (True, None)
    service.validate_password_strength.return_value = (True, [])
    service.hash_password.return_value = "hashed_password_123"
    return service

@pytest.fixture
def handler(mock_repository: AsyncMock, mock_domain_service: Mock) -> CreateUserHandler:
    """Create handler with mocked dependencies."""
    return CreateUserHandler(
        user_repository=mock_repository,
        user_service=mock_domain_service,
    )

class TestCreateUserHandler:
    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        handler: CreateUserHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test successful user creation."""
        command = CreateUserCommand(
            email="test@example.com",
            password="StrongPassword123!",
            username="testuser",
        )

        result = await handler.handle(command)

        assert result.is_ok()
        user = result.unwrap()
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self,
        handler: CreateUserHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test duplicate email rejection."""
        mock_repository.exists_by_email.return_value = True

        command = CreateUserCommand(
            email="existing@example.com",
            password="Password123!",
        )

        result = await handler.handle(command)

        assert result.is_err()
        error = result.unwrap_err()
        assert "already registered" in str(error).lower()
```

**Query Handlers**

```python
# tests/unit/application/users/queries/test_get_user_handlers.py
import pytest
from unittest.mock import AsyncMock
from application.users.queries import GetUserByIdHandler, GetUserByIdQuery

@pytest.fixture
def mock_repository() -> AsyncMock:
    """Mock user repository."""
    repo = AsyncMock()
    return repo

@pytest.fixture
def handler(mock_repository: AsyncMock) -> GetUserByIdHandler:
    """Create handler with mocked repository."""
    return GetUserByIdHandler(repository=mock_repository)

class TestGetUserByIdHandler:
    @pytest.mark.asyncio
    async def test_get_user_success(
        self,
        handler: GetUserByIdHandler,
        mock_repository: AsyncMock,
        sample_user: UserAggregate,
    ) -> None:
        """Test successful user retrieval."""
        mock_repository.get_by_id.return_value = sample_user

        query = GetUserByIdQuery(user_id="01HJ9K7...")
        result = await handler.handle(query)

        assert result.is_ok()
        user_data = result.unwrap()
        assert user_data["id"] == sample_user.id
        assert user_data["email"] == sample_user.email

    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self,
        handler: GetUserByIdHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test user not found returns None."""
        mock_repository.get_by_id.return_value = None

        query = GetUserByIdQuery(user_id="nonexistent")
        result = await handler.handle(query)

        assert result.is_ok()
        assert result.unwrap() is None
```

#### Infrastructure Layer

```python
# tests/unit/infrastructure/test_jwt_service.py
class TestJWTService:
    @pytest.fixture
    def jwt_service(self):
        return JWTService(
            secret_key="test-secret-key-at-least-32-chars",
            algorithm="HS256",
        )
    
    def test_create_access_token(self, jwt_service):
        token = jwt_service.create_access_token(
            user_id="123",
            roles=["admin"],
        )
        
        assert token is not None
        payload = jwt.decode(token, "test-secret-key-at-least-32-chars", algorithms=["HS256"])
        assert payload["sub"] == "123"
        assert payload["roles"] == ["admin"]
    
    def test_expired_token_raises(self, jwt_service):
        # Create expired token
        token = jwt_service.create_access_token(user_id="123")
        
        # Mock time to be past expiration
        with freeze_time(datetime.utcnow() + timedelta(hours=1)):
            with pytest.raises(UnauthorizedError):
                jwt_service.validate(token)
```

## Property-Based Testing

### Using Hypothesis

```python
# tests/properties/test_user_properties.py
from hypothesis import given, strategies as st, settings

class TestUserProperties:
    """
    **Feature: user-management, Property 1: User activation is idempotent**
    **Validates: Requirements 1.1**
    """
    
    @given(st.booleans())
    @settings(max_examples=100)
    def test_activate_then_deactivate_returns_to_original(self, initial_active: bool):
        """Activation followed by deactivation returns to original state."""
        user = User(id="123", email="test@example.com", is_active=initial_active)
        
        if not initial_active:
            user.activate()
        user.deactivate()
        
        assert user.is_active is False

    @given(st.emails())
    @settings(max_examples=100)
    def test_email_validation_accepts_valid_emails(self, email: str):
        """
        **Feature: user-management, Property 2: Email validation**
        **Validates: Requirements 1.2**
        """
        # Valid emails should not raise
        Email(email)  # Should not raise

    @given(st.text(min_size=1).filter(lambda x: "@" not in x))
    @settings(max_examples=100)
    def test_email_validation_rejects_invalid_emails(self, invalid_email: str):
        """Invalid emails (without @) should be rejected."""
        with pytest.raises(ValidationError):
            Email(invalid_email)
```

### Custom Strategies

```python
# tests/strategies.py
from hypothesis import strategies as st

@st.composite
def user_strategy(draw):
    """Generate random valid users."""
    return User(
        id=draw(st.text(min_size=26, max_size=26, alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ")),
        email=draw(st.emails()),
        name=draw(st.text(min_size=1, max_size=100)),
        is_active=draw(st.booleans()),
        roles=draw(st.lists(st.sampled_from(["admin", "user", "moderator"]), max_size=3)),
    )

@st.composite
def money_strategy(draw):
    """Generate random valid money amounts."""
    return Money(
        amount=draw(st.decimals(min_value=0, max_value=1000000, places=2)),
        currency=draw(st.sampled_from(["USD", "EUR", "GBP"])),
    )
```

## Integration Testing

### Database Integration

```python
# tests/integration/db/test_user_repository.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def session(test_db):
    async with test_db.session() as session:
        yield session
        await session.rollback()

@pytest.fixture
def repository(session):
    return UserRepository(session)

class TestUserRepository:
    async def test_add_and_get_user(self, repository):
        user = User(email="test@example.com", name="Test")
        
        created = await repository.add(user)
        retrieved = await repository.get(created.id)
        
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
    
    async def test_find_by_specification(self, repository):
        # Create test users
        await repository.add(User(email="active@example.com", is_active=True))
        await repository.add(User(email="inactive@example.com", is_active=False))
        
        spec = FieldSpecification("is_active", ComparisonOperator.EQ, True)
        results = await repository.find(spec)
        
        assert len(results) == 1
        assert results[0].email == "active@example.com"
```

### API Integration

```python
# tests/integration/api/test_users_api.py
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def auth_headers(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "password123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

class TestUsersAPI:
    async def test_create_user(self, client, auth_headers):
        response = await client.post(
            "/api/v1/users",
            json={"email": "new@example.com", "name": "New User"},
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        assert response.json()["email"] == "new@example.com"
    
    async def test_get_user_not_found(self, client, auth_headers):
        response = await client.get(
            "/api/v1/users/nonexistent",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        assert response.json()["type"].endswith("/not-found")
```

## End-to-End Testing

### Complete User Lifecycle

```python
# tests/e2e/test_users_complete_flow.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

@pytest.mark.e2e
class TestUsersCompleteFlow:
    def test_complete_user_lifecycle(self, client: TestClient) -> None:
        """Test complete CRUD lifecycle for a user.

        Flow:
        1. CREATE user
        2. GET user by ID
        3. UPDATE user
        4. GET updated user
        5. DELETE user
        6. Verify user is deactivated
        """
        # CREATE
        create_response = client.post("/api/v1/users", json={
            "email": "e2e.test@example.com",
            "password": "SecurePassword123!",
            "username": "e2euser",
            "display_name": "E2E Test User",
        })
        assert create_response.status_code == 201
        created_user = create_response.json()
        user_id = created_user["id"]

        # GET
        get_response = client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == 200
        user = get_response.json()
        assert user["email"] == "e2e.test@example.com"
        assert user["username"] == "e2euser"

        # UPDATE
        update_response = client.patch(f"/api/v1/users/{user_id}", json={
            "username": "e2euser_updated",
            "display_name": "Updated Name",
        })
        assert update_response.status_code == 200
        updated_user = update_response.json()
        assert updated_user["username"] == "e2euser_updated"

        # GET updated
        get_updated_response = client.get(f"/api/v1/users/{user_id}")
        assert get_updated_response.status_code == 200
        assert get_updated_response.json()["username"] == "e2euser_updated"

        # DELETE (soft delete)
        delete_response = client.delete(
            f"/api/v1/users/{user_id}",
            params={"reason": "E2E test cleanup"},
        )
        assert delete_response.status_code == 204

        # Verify deactivation
        get_deleted_response = client.get(f"/api/v1/users/{user_id}")
        assert get_deleted_response.status_code == 404

    @pytest.mark.e2e
    def test_duplicate_email_prevention(self, client: TestClient) -> None:
        """Test that duplicate emails are prevented."""
        # Create first user
        first_user = client.post("/api/v1/users", json={
            "email": "duplicate@example.com",
            "password": "Password123!",
        })
        assert first_user.status_code == 201

        # Attempt duplicate
        duplicate_user = client.post("/api/v1/users", json={
            "email": "duplicate@example.com",
            "password": "AnotherPassword123!",
        })
        assert duplicate_user.status_code == 400
        assert "already registered" in duplicate_user.json()["detail"].lower()

    @pytest.mark.e2e
    def test_pagination_and_filtering(self, client: TestClient) -> None:
        """Test user list pagination and filtering."""
        # Create multiple users
        for i in range(15):
            client.post("/api/v1/users", json={
                "email": f"paginate{i}@example.com",
                "password": "Password123!",
            })

        # Test pagination
        page1 = client.get("/api/v1/users", params={"page": 1, "page_size": 10})
        assert page1.status_code == 200
        assert len(page1.json()["items"]) == 10

        page2 = client.get("/api/v1/users", params={"page": 2, "page_size": 10})
        assert page2.status_code == 200
        assert len(page2.json()["items"]) >= 5
```

## Test Factories

### Using polyfactory

```python
# tests/factories/user_factory.py
from polyfactory.factories.pydantic_factory import ModelFactory

class UserFactory(ModelFactory):
    __model__ = User
    
    @classmethod
    def email(cls) -> str:
        return f"user_{cls.__random__.randint(1, 10000)}@example.com"
    
    @classmethod
    def is_active(cls) -> bool:
        return True

# Usage
user = UserFactory.build()
users = UserFactory.batch(10)
```

## Test Configuration

### conftest.py

```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def app():
    from src.main import create_app
    return create_app(testing=True)
```

## Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Specific test types
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/properties/

# Specific test file
uv run pytest tests/unit/domain/test_user.py

# With verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

## Coverage Requirements

| Type | Minimum Coverage |
|------|------------------|
| Unit Tests | 80% |
| Integration Tests | 60% |
| Overall | 75% |

## Related Documentation

- [Deployment](../operations/deployment.md)
