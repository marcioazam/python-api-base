# Padrões de Implementação

Este documento descreve os padrões de design utilizados no Python API Base e como implementá-los.

## 1. Specification Pattern

O padrão Specification encapsula regras de negócio em objetos composáveis.

### Localização
`src/domain/common/specification.py`

### Operadores Disponíveis

| Operador | Descrição | Exemplo |
|----------|-----------|---------|
| `EQ` | Igual | `equals("status", "active")` |
| `NE` | Diferente | `not_equals("status", "deleted")` |
| `GT` | Maior que | `greater_than("age", 18)` |
| `GE` | Maior ou igual | `greater_than_or_equal("score", 80)` |
| `LT` | Menor que | `less_than("price", 100)` |
| `LE` | Menor ou igual | `less_than_or_equal("quantity", 10)` |
| `CONTAINS` | Contém string | `contains("name", "John")` |
| `STARTS_WITH` | Começa com | `starts_with("email", "admin")` |
| `ENDS_WITH` | Termina com | `ends_with("email", "@company.com")` |
| `IN` | Está na lista | `in_list("status", ["active", "pending"])` |
| `IS_NULL` | É nulo | `is_null("deleted_at")` |
| `IS_NOT_NULL` | Não é nulo | `is_not_null("verified_at")` |

### Composição de Specifications

```python
from domain.common.specification import equals, greater_than, is_null

# Specifications individuais
active_users = equals("is_active", True)
premium_users = equals("subscription", "premium")
not_deleted = is_null("deleted_at")

# Composição com AND
active_premium = active_users.and_spec(premium_users)

# Composição com OR
any_special = active_users.or_spec(premium_users)

# Negação
inactive_users = active_users.not_spec()

# Composição complexa
target_users = (
    active_users
    .and_spec(premium_users)
    .and_spec(not_deleted)
)
```

### Conversão para SQLAlchemy

```python
from infrastructure.db.query_builder import SpecificationToSQLAlchemy

converter = SpecificationToSQLAlchemy()
filter_clause = converter.to_filter(target_users, UserModel)

# Uso em query
query = select(UserModel).where(filter_clause)
```

### Criando Specifications Customizadas

```python
from domain.common.specification import Specification

class ActiveUserSpecification(Specification[User]):
    def is_satisfied_by(self, user: User) -> bool:
        return user.is_active and user.deleted_at is None

class PremiumUserSpecification(Specification[User]):
    def __init__(self, min_subscription_days: int = 30):
        self.min_days = min_subscription_days

    def is_satisfied_by(self, user: User) -> bool:
        if user.subscription != "premium":
            return False
        days = (datetime.now() - user.subscription_start).days
        return days >= self.min_days
```

---

## 2. CQRS Pattern

Command Query Responsibility Segregation separa operações de leitura e escrita.

### Localização
`src/application/common/cqrs/`

### Command (Escrita)

```python
from dataclasses import dataclass
from application.common.cqrs import Command
from result import Result, Ok, Err

@dataclass
class CreateUserCommand(Command[User]):
    email: str
    name: str
    password: str

    async def execute(
        self,
        repository: IUserRepository,
        password_hasher: PasswordHasher,
    ) -> Result[User, str]:
        # Validação
        if await repository.exists_by_email(self.email):
            return Err("Email already exists")

        # Criação
        user = User(
            id=generate_ulid(),
            email=self.email,
            name=self.name,
            password_hash=password_hasher.hash(self.password),
            created_at=datetime.utcnow(),
        )

        created_user = await repository.create(user)
        return Ok(created_user)
```

### Query (Leitura)

```python
from dataclasses import dataclass
from application.common.cqrs import Query

@dataclass
class GetUserQuery(Query[UserDTO | None]):
    user_id: str
    cacheable: bool = True
    cache_ttl: int = 300

    async def execute(
        self,
        repository: IUserRepository,
    ) -> UserDTO | None:
        user = await repository.get(self.user_id)
        if user is None:
            return None
        return UserMapper.to_dto(user)

@dataclass
class ListUsersQuery(Query[list[UserDTO]]):
    skip: int = 0
    limit: int = 20
    filter_active: bool = True

    async def execute(
        self,
        repository: IUserRepository,
    ) -> list[UserDTO]:
        users = await repository.get_all(
            skip=self.skip,
            limit=self.limit,
            active_only=self.filter_active,
        )
        return [UserMapper.to_dto(u) for u in users]
```

### Handler Pattern

```python
from application.common.cqrs import CommandHandler, QueryHandler

class CreateUserHandler(CommandHandler[CreateUserCommand, User]):
    def __init__(
        self,
        repository: IUserRepository,
        password_hasher: PasswordHasher,
    ):
        self.repository = repository
        self.password_hasher = password_hasher

    async def handle(self, command: CreateUserCommand) -> Result[User, str]:
        return await command.execute(self.repository, self.password_hasher)
```

---

## 3. Repository Pattern

Abstrai o acesso a dados através de interfaces.

### Localização
- Protocol: `src/core/protocols/repository.py`
- Implementação: `src/infrastructure/db/repositories/`

### Protocol Base

```python
from typing import Protocol

class AsyncRepository[T, ID](Protocol):
    async def get(self, id: ID) -> T | None: ...
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]: ...
    async def create(self, entity: T) -> T: ...
    async def update(self, entity: T) -> T: ...
    async def delete(self, id: ID) -> bool: ...
    async def exists(self, id: ID) -> bool: ...
```

### Domain Repository Interface

```python
# src/domain/users/repository.py
class IUserRepository(AsyncRepository[User, str], Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def exists_by_email(self, email: str) -> bool: ...
```

### SQLAlchemy Implementation

```python
# src/infrastructure/db/repositories/user_repository.py
class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, id: str) -> User | None:
        return await self._session.get(UserModel, id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        model = UserModel(**user.dict())
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return User.from_orm(model)
```

### In-Memory Implementation (Testing)

```python
# src/infrastructure/db/repositories/in_memory.py
class InMemoryUserRepository(IUserRepository):
    def __init__(self):
        self._store: dict[str, User] = {}

    async def get(self, id: str) -> User | None:
        return self._store.get(id)

    async def get_by_email(self, email: str) -> User | None:
        for user in self._store.values():
            if user.email == email:
                return user
        return None

    async def create(self, user: User) -> User:
        self._store[user.id] = user
        return user
```

---

## 4. Resilience Patterns

Padrões para tolerância a falhas.

### Localização
`src/infrastructure/resilience/patterns.py`

### Circuit Breaker

```python
from infrastructure.resilience import CircuitBreaker, CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,    # Falhas para abrir
    success_threshold=3,    # Sucessos para fechar
    timeout=30.0,           # Segundos em half-open
)

circuit = CircuitBreaker(config)

async def call_external_api():
    return await circuit.execute(lambda: http_client.get("/api/data"))
```

### Retry com Exponential Backoff

```python
from infrastructure.resilience import Retry, RetryConfig

config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)

retry = Retry(config)

async def fetch_with_retry():
    return await retry.execute(lambda: http_client.get("/api/data"))
```

### Bulkhead (Limitador de Concorrência)

```python
from infrastructure.resilience import Bulkhead, BulkheadConfig

config = BulkheadConfig(
    max_concurrent=10,  # Máximo de chamadas simultâneas
    max_wait=5.0,       # Tempo máximo de espera
)

bulkhead = Bulkhead(config)

async def limited_call():
    return await bulkhead.execute(lambda: expensive_operation())
```

### Timeout

```python
from infrastructure.resilience import Timeout, TimeoutConfig

config = TimeoutConfig(timeout=30.0)
timeout = Timeout(config)

async def timed_call():
    return await timeout.execute(lambda: slow_operation())
```

### Composição de Patterns

```python
# Combinar múltiplos patterns
async def resilient_external_call():
    return await (
        circuit.execute(
            lambda: retry.execute(
                lambda: timeout.execute(
                    lambda: bulkhead.execute(
                        lambda: http_client.get("/api/data")
                    )
                )
            )
        )
    )
```

---

## 5. Cache Pattern

### Localização
`src/infrastructure/cache/`

### Decorator

```python
from infrastructure.cache import cached

@cached(ttl=300, key_builder=lambda user_id: f"user:{user_id}")
async def get_user(user_id: str) -> UserDTO:
    return await repository.get(user_id)
```

### Provider Direto

```python
from infrastructure.cache import RedisCacheProvider

cache = RedisCacheProvider(redis_client)

# Set
await cache.set("user:123", user_dto, ttl=300)

# Get
user = await cache.get("user:123")

# Delete
await cache.delete("user:123")

# Clear pattern
await cache.clear_pattern("user:*")
```

---

## Referências

- [ADR-005: Repository Pattern](adr/ADR-005-repository-pattern.md)
- [ADR-006: Specification Pattern](adr/ADR-006-specification-pattern.md)
- [ADR-007: CQRS Implementation](adr/ADR-007-cqrs-implementation.md)
- [ADR-008: Cache Strategy](adr/ADR-008-cache-strategy.md)
- [ADR-009: Resilience Patterns](adr/ADR-009-resilience-patterns.md)
