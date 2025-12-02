# Bibliotecas e Dependências

## Visão Geral

Este documento lista todas as bibliotecas utilizadas no Python API Base, organizadas por categoria.

## 1. Web Framework

### FastAPI (0.115+)

**Propósito:** Framework web assíncrono de alta performance.

```python
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
```

**Uso no projeto:**
- Definição de rotas REST
- Injeção de dependências
- Validação automática de requests
- Documentação OpenAPI automática

### Uvicorn (0.32+)

**Propósito:** Servidor ASGI de alta performance.

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Configurações:**
- HTTP/1.1 e HTTP/2
- WebSocket support
- Hot reload em desenvolvimento

---

## 2. Validação e Serialização

### Pydantic (2.9+)

**Propósito:** Validação de dados e serialização.

```python
from pydantic import BaseModel, Field, field_validator, model_validator
```

**Uso no projeto:**
- DTOs (Data Transfer Objects)
- Request/Response models
- Validação de entrada
- Serialização JSON

### Pydantic Settings (2.6+)

**Propósito:** Gerenciamento de configurações.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
    )
```

**Features:**
- Carregamento de .env
- Validação de tipos
- Nested settings
- Secrets handling

---

## 3. ORM e Database

### SQLAlchemy (2.0+)

**Propósito:** ORM e toolkit SQL.

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
```

**Uso no projeto:**
- Mapeamento objeto-relacional
- Query building
- Connection pooling
- Transações assíncronas

### SQLModel (0.0.22+)

**Propósito:** Integração SQLAlchemy + Pydantic.

```python
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    email: str = Field(unique=True)
```

**Benefícios:**
- Modelos únicos para ORM e API
- Validação Pydantic integrada
- Type hints completos

### AsyncPG (0.30+)

**Propósito:** Driver PostgreSQL assíncrono.

```python
# Usado internamente pelo SQLAlchemy
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"
```

### Alembic (1.14+)

**Propósito:** Migrations de banco de dados.

```bash
alembic revision --autogenerate -m "Add users table"
alembic upgrade head
```

**Estrutura:**
```
alembic/
├── env.py
├── script.py.mako
└── versions/
    ├── 001_initial.py
    └── 002_add_users.py
```

---

## 4. Injeção de Dependência

### Dependency Injector (4.42+)

**Propósito:** Container IoC para DI.

```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    db_session = providers.Factory(
        get_async_session,
        database_url=config.database.url,
    )
```

**Patterns:**
- Factory providers
- Singleton providers
- Configuration providers
- Wiring automático

---

## 5. Observabilidade

### Structlog (24.4+)

**Propósito:** Logging estruturado.

```python
import structlog

logger = structlog.get_logger()
logger.info("user_created", user_id="123", email="user@example.com")
```

**Output JSON:**
```json
{
    "event": "user_created",
    "user_id": "123",
    "email": "user@example.com",
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "info"
}
```

### OpenTelemetry (1.28+)

**Propósito:** Distributed tracing e metrics.

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order_id", order_id)
```

**Componentes:**
- `opentelemetry-api` - API base
- `opentelemetry-sdk` - Implementação
- `opentelemetry-instrumentation-fastapi` - Auto-instrumentação
- `opentelemetry-exporter-otlp` - Export para collectors

### Prometheus Client (0.20+)

**Propósito:** Métricas Prometheus.

```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
```

---

## 6. Cache e Storage

### Redis (5.0+)

**Propósito:** Cache e message broker.

```python
import redis.asyncio as redis

client = redis.from_url("redis://localhost:6379")
await client.set("key", "value", ex=3600)
```

**Uso no projeto:**
- Cache de dados
- Token blacklist
- Rate limiting
- Session storage

### MinIO (7.2+)

**Propósito:** Object storage S3-compatible.

```python
from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,
)
```

---

## 7. Messaging

### AIOKafka (0.10+)

**Propósito:** Cliente Kafka assíncrono.

```python
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
await producer.send("topic", value=b"message")
```

### Elasticsearch (8.12+)

**Propósito:** Search engine e analytics.

```python
from elasticsearch import AsyncElasticsearch

es = AsyncElasticsearch(["http://localhost:9200"])
await es.index(index="logs", document={"message": "test"})
```

### Cassandra Driver (3.29+)

**Propósito:** Cliente ScyllaDB/Cassandra.

```python
from cassandra.cluster import Cluster

cluster = Cluster(["localhost"])
session = cluster.connect("keyspace")
```

---

## 8. Segurança

### SlowAPI (0.1.9+)

**Propósito:** Rate limiting para FastAPI.

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/resource")
@limiter.limit("100/minute")
async def get_resource():
    pass
```

### Passlib (1.7.4+)

**Propósito:** Hashing de senhas.

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
hashed = pwd_context.hash("password")
verified = pwd_context.verify("password", hashed)
```

**Algoritmos:**
- Argon2 (recomendado)
- bcrypt
- PBKDF2

### Python-Jose (3.3+)

**Propósito:** JWT handling.

```python
from jose import jwt

token = jwt.encode(
    {"sub": "user_id", "exp": datetime.utcnow() + timedelta(hours=1)},
    secret_key,
    algorithm="HS256"
)
payload = jwt.decode(token, secret_key, algorithms=["HS256"])
```

### Cryptography (41+)

**Propósito:** Primitivas criptográficas.

```python
from cryptography.fernet import Fernet

key = Fernet.generate_key()
f = Fernet(key)
encrypted = f.encrypt(b"secret data")
```

---

## 9. Utilitários

### Python-ULID (3.0+)

**Propósito:** Geração de ULIDs.

```python
from ulid import ULID

ulid = ULID()
print(str(ulid))  # "01ARZ3NDEKTSV4RRFFQ69G5FAV"
```

**Vantagens sobre UUID:**
- Ordenável por tempo
- Mais compacto
- URL-safe

### UUID7 (0.1+)

**Propósito:** UUIDs v7 (time-ordered).

```python
from uuid6 import uuid7

id = uuid7()  # Time-ordered UUID
```

### Pendulum (3.0+)

**Propósito:** Manipulação de datas/horas.

```python
import pendulum

now = pendulum.now("America/Sao_Paulo")
tomorrow = now.add(days=1)
```

### Tenacity (9.0+)

**Propósito:** Retry com backoff.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_external_api():
    pass
```

### HTTPX (0.28+)

**Propósito:** Cliente HTTP assíncrono.

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com")
```

---

## 10. GraphQL

### Strawberry GraphQL (0.252+)

**Propósito:** Framework GraphQL type-safe.

```python
import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class User:
    id: str
    name: str

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: str) -> User:
        return get_user(id)

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)
```

---

## 11. CLI

### Typer (0.12+)

**Propósito:** CLI framework.

```python
import typer

app = typer.Typer()

@app.command()
def hello(name: str):
    typer.echo(f"Hello {name}")

if __name__ == "__main__":
    app()
```

---

## 12. Desenvolvimento

### Pytest (8.3+)

**Propósito:** Framework de testes.

```python
import pytest

@pytest.mark.asyncio
async def test_create_user():
    user = await create_user("test@example.com")
    assert user.email == "test@example.com"
```

### Hypothesis (6.115+)

**Propósito:** Property-based testing.

```python
from hypothesis import given, strategies as st

@given(st.emails())
def test_email_validation(email):
    result = validate_email(email)
    assert result.is_valid
```

### Polyfactory (2.17+)

**Propósito:** Factory para testes.

```python
from polyfactory.factories.pydantic_factory import ModelFactory

class UserFactory(ModelFactory):
    __model__ = User

user = UserFactory.build()
```

### Ruff (0.8+)

**Propósito:** Linter e formatter.

```bash
ruff check .      # Lint
ruff format .     # Format
```

### MyPy (1.13+)

**Propósito:** Type checking.

```bash
mypy src/ --strict
```

### Bandit (1.7+)

**Propósito:** Security linting.

```bash
bandit -r src/
```

---

## 13. Matriz de Versões

| Biblioteca | Versão Mínima | Propósito |
|------------|---------------|-----------|
| fastapi | 0.115.0 | Web framework |
| uvicorn | 0.32.0 | ASGI server |
| pydantic | 2.9.0 | Validation |
| sqlalchemy | 2.0.36 | ORM |
| sqlmodel | 0.0.22 | SQLAlchemy + Pydantic |
| asyncpg | 0.30.0 | PostgreSQL driver |
| alembic | 1.14.0 | Migrations |
| structlog | 24.4.0 | Logging |
| opentelemetry-api | 1.28.0 | Tracing |
| redis | 5.0.0 | Cache |
| minio | 7.2.0 | Object storage |
| aiokafka | 0.10.0 | Kafka client |
| elasticsearch | 8.12.0 | Search |
| slowapi | 0.1.9 | Rate limiting |
| passlib | 1.7.4 | Password hashing |
| python-jose | 3.3.0 | JWT |
| httpx | 0.28.0 | HTTP client |
| strawberry-graphql | 0.252.0 | GraphQL |
| typer | 0.12.0 | CLI |
| pytest | 8.3.0 | Testing |
| hypothesis | 6.115.0 | Property testing |
| ruff | 0.8.0 | Linting |
| mypy | 1.13.0 | Type checking |

---

## 14. Instalação

### Produção

```bash
# Com uv (recomendado)
uv sync

# Com pip
pip install -e .
```

### Desenvolvimento

```bash
# Com uv
uv sync --dev

# Com pip
pip install -e ".[dev]"
```

### Dependências Opcionais

```bash
# Apenas testes
pip install -e ".[test]"

# Apenas documentação
pip install -e ".[docs]"
```
