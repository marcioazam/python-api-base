# Guia de Testes

Este documento descreve a estratégia de testes do Python API Base.

## Estrutura de Testes

```
tests/
├── conftest.py              # Fixtures compartilhadas
├── factories/               # Test factories (Polyfactory)
│   ├── __init__.py
│   ├── user_factory.py
│   └── item_factory.py
├── unit/                    # Testes unitários
│   ├── domain/
│   ├── application/
│   └── infrastructure/
├── integration/             # Testes de integração
│   ├── api/
│   └── repositories/
├── properties/              # Property-based tests
│   └── test_*.py
└── e2e/                     # End-to-end tests
    └── test_*.py
```

## 1. Testes Unitários

### Estrutura

```python
# tests/unit/domain/users/test_user_entity.py
import pytest
from domain.users.entities import User
from domain.users.value_objects import Email

class TestUser:
    def test_create_user_with_valid_data(self):
        user = User(
            id="user-123",
            email="test@example.com",
            name="Test User",
        )
        assert user.id == "user-123"
        assert user.email == "test@example.com"

    def test_user_email_validation(self):
        with pytest.raises(ValueError):
            Email("invalid-email")
```

### Fixtures

```python
# tests/conftest.py
import pytest
from datetime import datetime

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
    return InMemoryUserRepository()
```

### Mocking

```python
# tests/unit/application/users/test_create_user.py
from unittest.mock import AsyncMock, MagicMock
import pytest

@pytest.mark.asyncio
async def test_create_user_command():
    # Arrange
    repository = AsyncMock()
    repository.exists_by_email.return_value = False
    repository.create.return_value = User(id="new-id", ...)

    command = CreateUserCommand(
        email="new@example.com",
        name="New User",
        password="securepassword123",
    )

    # Act
    result = await command.execute(repository)

    # Assert
    assert result.is_ok()
    repository.create.assert_called_once()
```

## 2. Property-Based Tests (Hypothesis)

### Configuração

```python
# tests/conftest.py
from hypothesis import settings, Verbosity

settings.register_profile("ci", max_examples=100)
settings.register_profile("dev", max_examples=10)
settings.load_profile("dev")
```

### Strategies Básicas

```python
from hypothesis import given, strategies as st

@given(st.emails())
def test_email_validation(email: str):
    """Qualquer email válido deve ser aceito."""
    result = validate_email(email)
    assert result.is_valid

@given(st.text(min_size=1, max_size=100))
def test_name_normalization(name: str):
    """Normalização deve ser idempotente."""
    normalized = normalize_name(name)
    assert normalize_name(normalized) == normalized
```

### Custom Generators

```python
# tests/factories/strategies.py
from hypothesis import strategies as st
from domain.users.entities import User

@st.composite
def users(draw):
    """Generate random valid users."""
    return User(
        id=draw(st.text(min_size=10, max_size=26, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")))),
        email=draw(st.emails()),
        name=draw(st.text(min_size=2, max_size=100)),
        is_active=draw(st.booleans()),
        created_at=draw(st.datetimes()),
    )

@st.composite
def orders(draw):
    """Generate random valid orders."""
    items = draw(st.lists(order_items(), min_size=1, max_size=10))
    return Order(
        id=draw(st.text(min_size=10, max_size=26)),
        customer_id=draw(st.text(min_size=10, max_size=26)),
        items=items,
        total=sum(item.subtotal for item in items),
        status=draw(st.sampled_from(OrderStatus)),
        created_at=draw(st.datetimes()),
    )
```

### Domain Invariants

```python
# tests/properties/test_order_invariants.py
from hypothesis import given
from tests.factories.strategies import orders

class TestOrderInvariants:
    @given(orders())
    def test_order_total_equals_sum_of_items(self, order):
        """Order total must equal sum of item subtotals."""
        expected_total = sum(item.subtotal for item in order.items)
        assert order.total == expected_total

    @given(orders())
    def test_order_has_at_least_one_item(self, order):
        """Order must have at least one item."""
        assert len(order.items) >= 1
```

### Specification Properties

```python
# tests/properties/test_specification_properties.py
from hypothesis import given, strategies as st
from domain.common.specification import equals, greater_than

class TestSpecificationComposition:
    @given(st.integers(), st.integers())
    def test_and_spec_is_commutative(self, a, b):
        """AND composition should be commutative."""
        spec1 = equals("value", a)
        spec2 = equals("value", b)

        obj = {"value": a}

        result1 = spec1.and_spec(spec2).is_satisfied_by(obj)
        result2 = spec2.and_spec(spec1).is_satisfied_by(obj)

        assert result1 == result2

    @given(st.integers())
    def test_not_not_is_identity(self, value):
        """Double negation should be identity."""
        spec = equals("value", value)
        obj = {"value": value}

        original = spec.is_satisfied_by(obj)
        double_negated = spec.not_spec().not_spec().is_satisfied_by(obj)

        assert original == double_negated
```

## 3. Testes de Integração

### Database Setup

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

### API Tests

```python
# tests/integration/api/test_users_api.py
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
        json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    response = await client.get("/api/v1/users/nonexistent")
    assert response.status_code == 404
```

### Repository Tests

```python
# tests/integration/repositories/test_user_repository.py
import pytest
from infrastructure.db.repositories import UserRepository

@pytest.mark.asyncio
async def test_create_and_get_user(db_session):
    repository = UserRepository(db_session)

    user = User(
        id="user-123",
        email="test@example.com",
        name="Test User",
    )

    created = await repository.create(user)
    assert created.id == "user-123"

    retrieved = await repository.get("user-123")
    assert retrieved is not None
    assert retrieved.email == "test@example.com"
```

## 4. Test Factories (Polyfactory)

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

# Usage
user = UserFactory.build()
users = UserFactory.batch(10)
```

## 5. Coverage

### Requisitos

- Cobertura mínima: **80%**
- Cobertura de branches: **75%**

### Configuração

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/migrations/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
fail_under = 80
```

### Executando

```bash
# Rodar testes com coverage
pytest --cov=src --cov-report=html --cov-report=term

# Ver relatório
open htmlcov/index.html
```

## 6. CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --dev

      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Comandos Úteis

```bash
# Rodar todos os testes
pytest

# Rodar testes específicos
pytest tests/unit/
pytest tests/integration/
pytest tests/properties/

# Rodar com verbose
pytest -v

# Rodar teste específico
pytest tests/unit/domain/users/test_user.py::TestUser::test_create_user

# Rodar testes marcados
pytest -m "not slow"

# Rodar com paralelismo
pytest -n auto

# Rodar property tests com mais exemplos
pytest tests/properties/ --hypothesis-profile=ci
```

## Referências

- [pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Polyfactory Documentation](https://polyfactory.litestar.dev/)
