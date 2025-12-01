<p align="center">
  <img src="logo.png" alt="Base API Logo" width="200" />
</p>

<h1 align="center">Base API - Python Version</h1>

<p align="center">
  <strong>Framework REST API genérico e pronto para produção, construído com FastAPI e Clean Architecture</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-green.svg" alt="FastAPI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

---

## Visão Geral

Base API é um framework REST API reutilizável projetado para acelerar o desenvolvimento backend com Python. Fornece uma base sólida baseada nos princípios de Clean Architecture, aproveitando Python Generics para maximizar reuso de código e minimizar boilerplate.

O framework inclui tudo necessário para produção: operações CRUD genéricas type-safe, autenticação JWT com RBAC, injeção de dependência, logging estruturado, middlewares de segurança, migrations de banco de dados e infraestrutura completa de testes com property-based tests.

### Principais Destaques

- **CRUD Zero Boilerplate** - Crie endpoints REST completos com apenas 3 arquivos: entidade, use case e router
- **Generics Type-Safe** - `IRepository[T]`, `BaseUseCase[T]`, `GenericCRUDRouter[T]` com suporte completo de IDE
- **Autenticação Completa** - JWT com access/refresh tokens, revogação via Redis, RBAC com composição de permissões
- **Pronto para Produção** - Rate limiting, headers de segurança, request tracing, health checks inclusos
- **Padrões de Resiliência** - Circuit breaker, retry com backoff exponencial, domain events, CQRS
- **Observabilidade** - OpenTelemetry (traces, metrics), structlog (JSON), correlação de logs
- **Geração de Código** - Scaffold de novas entidades com `python scripts/generate_entity.py`
- **166+ Testes** - Testes unitários, integração, property-based (33 arquivos) e load tests com k6

## Arquitetura

```
src/my_app/
├── core/           # Configuração, container DI, exceções, autenticação
│   └── auth/       # JWT, RBAC, password policy
├── shared/         # Classes base genéricas (Repository, UseCase, Router, DTOs)
├── domain/         # Entidades, value objects, interfaces de repositório
├── application/    # Use cases, mappers, DTOs
├── adapters/       # Rotas API, middleware, implementações de repositório
└── infrastructure/ # Database, logging, observability, audit
```

O projeto segue Clean Architecture com quatro camadas principais:
- **Domain** - Entidades de negócio e interfaces de repositório
- **Application** - Use cases orquestrando lógica de negócio
- **Adapters** - Rotas API, middleware, implementações concretas de repositório
- **Infrastructure** - Sessões de banco, logging, telemetria, auditoria

## Início Rápido

### Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recomendado) ou pip
- Docker & Docker Compose

### Instalação

```bash
git clone https://github.com/example/my-api.git
cd my-api

# Instalar com uv
uv sync --dev

# Ou com pip
pip install -e ".[dev]"
```

### Configuração

```bash
cp .env.example .env
# Edite .env - Obrigatório: SECURITY__SECRET_KEY (mín 32 chars)
```

### Executando

```bash
# Iniciar banco de dados
docker-compose up -d postgres redis

# Executar migrations
python scripts/migrate.py upgrade head

# Iniciar API
uv run uvicorn my_app.main:app --reload
```

### Pontos de Acesso

| Endpoint | Descrição |
|----------|-----------|
| http://localhost:8000 | Base da API |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health/live | Liveness Check |
| http://localhost:8000/health/ready | Readiness Check |

## Criando uma Nova Entidade

1. **Entidade** (`domain/entities/product.py`):
```python
class Product(SQLModel, table=True):
    id: str = Field(default_factory=generate_ulid, primary_key=True)
    name: str
    price: float
```

2. **Use Case** (`application/use_cases/product_use_case.py`):
```python
class ProductUseCase(BaseUseCase[Product, ProductCreate, ProductUpdate, ProductResponse]):
    pass
```

3. **Router** (`adapters/api/routes/products.py`):
```python
router = GenericCRUDRouter(
    prefix="/products",
    tags=["Products"],
    response_model=ProductResponse,
    create_model=ProductCreate,
    update_model=ProductUpdate,
    use_case_dependency=get_product_use_case,
)
```

Ou use o gerador: `python scripts/generate_entity.py product --fields "name:str,price:float"`

### Opções do Gerador

```bash
# Básico
python scripts/generate_entity.py product --fields "name:str,price:float"

# Com domain events
python scripts/generate_entity.py order --fields "total:float,status:str" --with-events

# Com caching
python scripts/generate_entity.py user --fields "email:str,name:str" --with-cache

# Preview sem criar arquivos
python scripts/generate_entity.py product --dry-run
```

## Autenticação & Autorização

### JWT Authentication

```python
from my_app.core.auth.jwt import JWTService

jwt_service = JWTService(secret_key="...", algorithm="HS256")

# Criar tokens
access_token = jwt_service.create_access_token(user_id="123", roles=["admin"])
refresh_token = jwt_service.create_refresh_token(user_id="123")

# Validar token
payload = jwt_service.verify_token(access_token)
```

### Token Revocation

```python
from my_app.infrastructure.auth.token_store import TokenStore

token_store = TokenStore(redis_client)

# Revogar token
await token_store.revoke_token(token_jti, expires_at)

# Verificar se está revogado
is_revoked = await token_store.is_revoked(token_jti)
```

### RBAC (Role-Based Access Control)

```python
from my_app.core.auth.rbac import RBACService, Role, Permission

# Definir roles com permissões
admin_role = Role(name="admin", permissions=[
    Permission(resource="users", action="read"),
    Permission(resource="users", action="write"),
])

rbac = RBACService()
rbac.register_role(admin_role)

# Verificar permissão
has_access = rbac.has_permission(user_roles=["admin"], resource="users", action="write")
```

### Password Policy

```python
from my_app.core.auth.password_policy import PasswordPolicy

policy = PasswordPolicy(min_length=12, require_uppercase=True, require_special=True)
result = policy.validate("MyP@ssw0rd123")

if not result.is_valid:
    print(result.errors)
```

## Recursos Avançados

### Caching

```python
from my_app.shared.caching import cached, InMemoryCacheProvider, CacheConfig

# Decorator simples
@cached(ttl=300)
async def get_user(user_id: str) -> User:
    return await db.fetch_user(user_id)

# Com provider customizado
cache = InMemoryCacheProvider(CacheConfig(max_size=1000, ttl=3600))

@cached(ttl=60, cache_provider=cache)
async def expensive_query() -> list:
    return await db.complex_query()
```

### CQRS

```python
from my_app.shared.cqrs import Command, Query, CommandBus, QueryBus
from my_app.shared.result import Ok, Result

# Command
@dataclass
class CreateOrderCommand(Command[str, str]):
    customer_id: str
    items: list[str]
    
    async def execute(self) -> Result[str, str]:
        return Ok("order-123")

# Query
@dataclass
class GetOrderQuery(Query[dict]):
    order_id: str
    cacheable: bool = True
    
    async def execute(self) -> dict:
        return {"id": self.order_id, "status": "pending"}

# Uso
bus = CommandBus()
bus.register(CreateOrderCommand, handler)
result = await bus.dispatch(CreateOrderCommand(customer_id="123", items=["item1"]))
```

### Specifications

```python
from my_app.shared.advanced_specification import (
    FieldSpecification, ComparisonOperator, SpecificationBuilder
)

# Specification simples
active_users = FieldSpecification("is_active", ComparisonOperator.EQ, True)
premium = FieldSpecification("tier", ComparisonOperator.EQ, "premium")

# Composição
active_premium = active_users.and_(premium)

# Builder fluente
spec = (
    SpecificationBuilder()
    .where("status", ComparisonOperator.EQ, "active")
    .and_where("price", ComparisonOperator.GT, 100)
    .build()
)

# Uso com SQLAlchemy
query = select(Product).where(spec.to_sql_condition(Product))
```

### Circuit Breaker

```python
from my_app.shared.circuit_breaker import circuit_breaker, CircuitBreaker

# Decorator
@circuit_breaker("external-api", failure_threshold=5, recovery_timeout=30)
async def call_external_service():
    return await http_client.get("https://api.example.com")

# Classe
cb = CircuitBreaker(name="payment-gateway", failure_threshold=3)
async with cb:
    result = await process_payment()
```

### Retry Pattern

```python
from my_app.shared.retry import retry, RETRY_STANDARD, RETRY_FAST

@retry(config=RETRY_STANDARD)  # 3 tentativas, backoff exponencial
async def unreliable_operation():
    return await some_flaky_service()

@retry(config=RETRY_FAST)  # 2 tentativas, delays curtos
async def quick_retry():
    return await another_service()
```

### Domain Events

```python
from my_app.shared.events import event_bus, EntityCreatedEvent

# Subscribe
@event_bus.subscribe("item.created")
async def handle_item_created(event: EntityCreatedEvent):
    await send_notification(event.entity_id)

# Publish
await event_bus.publish(EntityCreatedEvent(
    entity_type="item",
    entity_id="123"
))
```

### Tracing

```python
from my_app.infrastructure.observability.telemetry import traced

@traced(name="process_payment", attributes={"provider": "stripe"})
async def process_payment(order_id: str) -> bool:
    # Span criado automaticamente
    # Exceções registradas como eventos
    return await stripe.charge(order_id)
```

## Segurança

O framework implementa múltiplas camadas de segurança:

| Recurso | Implementação |
|---------|---------------|
| Autenticação | JWT com access (30min) e refresh tokens (7 dias) |
| Autorização | RBAC com composição de permissões |
| Rate Limiting | slowapi com limites configuráveis |
| Headers | CSP, HSTS, X-Frame-Options, X-Content-Type-Options |
| Senhas | Argon2 hashing + política configurável |
| Input | Validação Pydantic + sanitização |
| Tokens | Revogação via Redis blacklist |
| Logs | Redação automática de PII |

## Configuração

### Variáveis de Ambiente

```bash
# Aplicação
APP_NAME=My API
DEBUG=false
VERSION=1.0.0

# Database
DATABASE__URL=postgresql+asyncpg://user:pass@localhost/mydb
DATABASE__POOL_SIZE=10

# Segurança
SECURITY__SECRET_KEY=your-secret-key-min-32-chars
SECURITY__CORS_ORIGINS=["http://localhost:3000"]
SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES=30
SECURITY__REFRESH_TOKEN_EXPIRE_DAYS=7

# Observabilidade
OBSERVABILITY__LOG_LEVEL=INFO
OBSERVABILITY__LOG_FORMAT=json
OBSERVABILITY__OTLP_ENDPOINT=http://localhost:4317
OBSERVABILITY__SERVICE_NAME=my-api
```

Gere documentação completa: `python scripts/generate_config_docs.py --output docs/configuration.md`

## Testes

```bash
# Todos os testes
uv run pytest

# Com cobertura
uv run pytest --cov=src/my_app --cov-report=html

# Por tipo
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/properties/
```

### Property-Based Tests

O projeto inclui 33 arquivos de testes property-based com Hypothesis cobrindo:
- JWT token round-trip e validação
- RBAC permission composition
- Repository CRUD consistency
- Cache invalidation
- Security headers presence
- Error response format (RFC 7807)
- Token revocation
- Circuit breaker state transitions
- Rate limiter response format
- Password policy validation
- Sanitization e mais...

## Testes de Carga

O projeto inclui testes de carga usando [k6](https://k6.io/).

### Pré-requisitos

Instale o k6: https://k6.io/docs/get-started/installation/

### Executando

```bash
# Smoke test (verificação básica)
k6 run tests/load/smoke.js

# Stress test (encontrar limites)
k6 run tests/load/stress.js

# Com URL customizada
k6 run -e BASE_URL=http://api.example.com tests/load/smoke.js
```

## Desenvolvimento

```bash
uv run ruff check .      # Lint
uv run ruff format .     # Formatação
uv run mypy src/         # Type check
uv run pre-commit run --all-files  # Todas as verificações
```

## Stack Tecnológica

| Categoria | Tecnologias |
|-----------|-------------|
| Framework | FastAPI, Pydantic v2, SQLModel |
| Banco de Dados | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Cache | Redis, aiocache |
| DI | dependency-injector |
| Observabilidade | structlog, OpenTelemetry |
| Testes | pytest, Hypothesis, polyfactory, k6 |
| Segurança | slowapi, passlib (Argon2), python-jose |

## Documentação

- [Arquitetura](docs/architecture.md) - Documentação detalhada da arquitetura
- [Resumo de Melhorias](docs/improvements-summary.md) - Melhorias e mudanças recentes
- [ADRs](docs/adr/) - Decisões arquiteturais documentadas
  - [ADR-001: JWT Authentication](docs/adr/ADR-001-jwt-authentication.md)
  - [ADR-002: RBAC Implementation](docs/adr/ADR-002-rbac-implementation.md)
  - [ADR-003: API Versioning](docs/adr/ADR-003-api-versioning.md)
  - [ADR-004: Token Revocation](docs/adr/ADR-004-token-revocation.md)

## Conformidade

| Padrão | Status |
|--------|--------|
| Clean Architecture | ✅ 100% |
| OWASP API Security Top 10 | ✅ 100% |
| 12-Factor App | ✅ 100% |
| RFC 7807 (Problem Details) | ✅ Implementado |
| RFC 8594 (Deprecation Headers) | ✅ Implementado |

## Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.
