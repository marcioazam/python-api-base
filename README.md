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

O framework inclui tudo necessário para produção: operações CRUD genéricas type-safe, injeção de dependência, logging estruturado, middlewares de segurança, migrations de banco de dados e infraestrutura completa de testes com property-based tests.

### Principais Destaques

- **CRUD Zero Boilerplate** - Crie endpoints REST completos com apenas 3 arquivos: entidade, use case e router
- **Generics Type-Safe** - `IRepository[T]`, `BaseUseCase[T]`, `GenericCRUDRouter[T]` com suporte completo de IDE
- **Pronto para Produção** - Rate limiting, headers de segurança, request tracing, health checks inclusos
- **Padrões de Resiliência** - Circuit breaker, retry com backoff exponencial, domain events
- **Geração de Código** - Scaffold de novas entidades com `python scripts/generate_entity.py`
- **148+ Testes** - Testes unitários, integração e property-based com Hypothesis

## Arquitetura

```
src/my_api/
├── core/           # Configuração, container DI, exceções
├── shared/         # Classes base genéricas (Repository, UseCase, Router, DTOs)
├── domain/         # Entidades, value objects, interfaces de repositório
├── application/    # Use cases, mappers, DTOs
├── adapters/       # Rotas API, middleware, implementações de repositório
└── infrastructure/ # Database, logging, serviços externos
```

O projeto segue Clean Architecture com quatro camadas principais:
- **Domain** - Entidades de negócio e interfaces de repositório
- **Application** - Use cases orquestrando lógica de negócio
- **Adapters** - Rotas API, middleware, implementações concretas de repositório
- **Infrastructure** - Sessões de banco, configuração de logging, integrações externas

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
uv run uvicorn my_api.main:app --reload
```

### Pontos de Acesso

| Endpoint | Descrição |
|----------|-----------|
| http://localhost:8000 | Base da API |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health/live | Health Check |

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

## Recursos Avançados

### Caching

```python
from my_api.shared.caching import cached, InMemoryCacheProvider, CacheConfig

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
from my_api.shared.cqrs import Command, Query, CommandBus, QueryBus
from my_api.shared.result import Ok, Result

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
from my_api.shared.advanced_specification import (
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

### Tracing

```python
from my_api.infrastructure.observability.telemetry import traced

@traced(name="process_payment", attributes={"provider": "stripe"})
async def process_payment(order_id: str) -> bool:
    # Span criado automaticamente
    # Exceções registradas como eventos
    return await stripe.charge(order_id)
```

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
uv run pytest --cov=src/my_api --cov-report=html

# Por tipo
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/properties/
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
| DI | dependency-injector |
| Observabilidade | structlog, OpenTelemetry |
| Testes | pytest, Hypothesis, polyfactory |
| Segurança | slowapi, passlib, python-jose |

## Documentação

- [Arquitetura](docs/architecture.md) - Documentação detalhada da arquitetura
- [Resumo de Melhorias](docs/improvements-summary.md) - Melhorias e mudanças recentes

## Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.
