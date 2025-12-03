# Unit Testing

## Overview

Testes unitários verificam componentes isolados sem dependências externas.

## Structure

```python
# tests/unit/domain/users/test_user_entity.py
import pytest
from domain.users.entities import User

class TestUser:
    def test_create_user_with_valid_data(self):
        user = User(id="123", email="test@example.com", name="Test")
        assert user.id == "123"
        assert user.email == "test@example.com"
    
    def test_user_activate(self):
        user = User(id="123", email="test@example.com", name="Test", is_active=False)
        user.activate()
        assert user.is_active is True
    
    def test_user_soft_delete(self):
        user = User(id="123", email="test@example.com", name="Test")
        user.soft_delete()
        assert user.is_deleted is True
```

## Fixtures

```python
# tests/conftest.py
@pytest.fixture
def sample_user():
    return User(
        id="user-123",
        email="test@example.com",
        name="Test User",
        created_at=datetime.utcnow(),
    )

@pytest.fixture
def mock_repository():
    return AsyncMock(spec=IUserRepository)
```

## Mocking

```python
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_create_user_command(mock_repository):
    mock_repository.exists_by_email.return_value = False
    mock_repository.create.return_value = User(id="new-id", email="test@example.com", name="Test")
    
    command = CreateUserCommand(email="test@example.com", name="Test", password="password123")
    result = await command.execute(mock_repository)
    
    assert result.is_ok()
    mock_repository.create.assert_called_once()
```

## Testing Value Objects

```python
class TestEmail:
    def test_valid_email(self):
        email = Email("test@example.com")
        assert email.value == "test@example.com"
    
    def test_invalid_email_raises(self):
        with pytest.raises(ValueError):
            Email("invalid-email")
    
    def test_email_domain(self):
        email = Email("user@example.com")
        assert email.domain == "example.com"
```

## Testing Specifications

```python
class TestSpecification:
    def test_equals_specification(self):
        spec = equals("status", "active")
        assert spec.is_satisfied_by({"status": "active"})
        assert not spec.is_satisfied_by({"status": "inactive"})
    
    def test_and_composition(self):
        spec = equals("status", "active").and_spec(greater_than("age", 18))
        assert spec.is_satisfied_by({"status": "active", "age": 25})
        assert not spec.is_satisfied_by({"status": "active", "age": 15})
```

## Best Practices

1. **One assertion per test** - When possible
2. **Descriptive names** - `test_<what>_<condition>_<expected>`
3. **Arrange-Act-Assert** - Clear structure
4. **Mock external dependencies** - Keep tests isolated
5. **Test edge cases** - Empty, null, boundary values
