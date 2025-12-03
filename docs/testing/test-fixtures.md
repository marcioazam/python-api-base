# Test Fixtures and Factories

## Overview

Fixtures e factories facilitam a criação de dados de teste consistentes e reutilizáveis.

## Pytest Fixtures

```python
# tests/conftest.py
import pytest
from datetime import datetime

@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id="user-123",
        email="test@example.com",
        name="Test User",
        is_active=True,
        created_at=datetime.utcnow(),
    )

@pytest.fixture
def sample_order(sample_user):
    """Create a sample order with items."""
    return Order(
        id="order-123",
        customer_id=sample_user.id,
        items=[
            OrderItem(product_id="prod-1", quantity=2, unit_price=Decimal("10.00")),
            OrderItem(product_id="prod-2", quantity=1, unit_price=Decimal("25.00")),
        ],
        status=OrderStatus.PENDING,
    )
```

## Polyfactory

```python
# tests/factories/user_factory.py
from polyfactory.factories.pydantic_factory import ModelFactory
from domain.users.entities import User

class UserFactory(ModelFactory):
    __model__ = User
    
    @classmethod
    def id(cls) -> str:
        return f"user-{cls.__faker__.uuid4()[:8]}"
    
    @classmethod
    def email(cls) -> str:
        return cls.__faker__.email()
    
    @classmethod
    def name(cls) -> str:
        return cls.__faker__.name()
    
    @classmethod
    def is_active(cls) -> bool:
        return True

# Usage
user = UserFactory.build()
users = UserFactory.batch(10)
inactive_user = UserFactory.build(is_active=False)
```

## Factory with Relationships

```python
class OrderItemFactory(ModelFactory):
    __model__ = OrderItem
    
    @classmethod
    def product_id(cls) -> str:
        return f"prod-{cls.__faker__.uuid4()[:8]}"
    
    @classmethod
    def quantity(cls) -> int:
        return cls.__faker__.random_int(min=1, max=10)
    
    @classmethod
    def unit_price(cls) -> Decimal:
        return Decimal(str(cls.__faker__.random_int(min=100, max=10000) / 100))

class OrderFactory(ModelFactory):
    __model__ = Order
    
    @classmethod
    def items(cls) -> list[OrderItem]:
        return OrderItemFactory.batch(cls.__faker__.random_int(min=1, max=5))
    
    @classmethod
    def total(cls) -> Decimal:
        # Will be calculated from items
        return Decimal("0")
```

## Async Fixtures

```python
@pytest.fixture
async def created_user(db_session):
    """Create and persist a user."""
    repository = UserRepository(db_session)
    user = UserFactory.build()
    return await repository.create(user)

@pytest.fixture
async def auth_token(created_user, jwt_service):
    """Generate auth token for user."""
    return jwt_service.create_access_token(
        user_id=created_user.id,
        roles=["user"],
    )
```

## Fixture Scopes

```python
@pytest.fixture(scope="session")
def db_engine():
    """Session-scoped database engine."""
    ...

@pytest.fixture(scope="module")
def app():
    """Module-scoped application."""
    ...

@pytest.fixture(scope="function")  # default
def sample_user():
    """Function-scoped user."""
    ...
```

## Parametrized Fixtures

```python
@pytest.fixture(params=["active", "inactive", "deleted"])
def user_status(request):
    """Parametrized user status."""
    return request.param

@pytest.fixture
def user_with_status(user_status):
    """User with parametrized status."""
    return UserFactory.build(
        is_active=user_status == "active",
        deleted_at=datetime.utcnow() if user_status == "deleted" else None,
    )
```

## Factory Traits

```python
class UserFactory(ModelFactory):
    __model__ = User
    
    class Meta:
        traits = {
            "admin": {"roles": ["admin", "user"]},
            "inactive": {"is_active": False},
            "deleted": {"deleted_at": datetime.utcnow()},
        }

# Usage
admin = UserFactory.build(traits=["admin"])
inactive_admin = UserFactory.build(traits=["admin", "inactive"])
```

## Best Practices

1. **Use factories for complex objects** - Not manual construction
2. **Keep fixtures simple** - Single responsibility
3. **Use appropriate scopes** - Minimize setup time
4. **Avoid fixture dependencies** - Keep tests independent
5. **Document fixtures** - Clear docstrings
