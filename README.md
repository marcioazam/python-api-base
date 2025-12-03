<p align="center">
  <img src="logo.png" alt="Python API Base Logo" width="200" />
</p>

<h1 align="center">Python API Base</h1>

<p align="center">
  <strong>Framework REST API enterprise-grade construído com FastAPI, Clean Architecture e Domain-Driven Design</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-green.svg" alt="FastAPI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/coverage-80%25+-brightgreen.svg" alt="Coverage"></a>
</p>

---

## Índice

- [Visão Geral](#visão-geral)
- [Características](#características)
- [Arquitetura](#arquitetura)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Início Rápido](#início-rápido)
- [Módulos](#módulos)
- [Padrões de Design](#padrões-de-design)
- [Autenticação e Autorização](#autenticação-e-autorização)
- [Recursos Avançados](#recursos-avançados)
- [Configuração](#configuração)
- [Testes](#testes)
- [Deploy](#deploy)
- [Comandos Úteis](#comandos-úteis)
- [Stack Tecnológica](#stack-tecnológica)
- [Documentação](#documentação)
- [Conformidade](#conformidade)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

---

## Visão Geral

Python API Base é um framework REST API reutilizável e pronto para produção, projetado para acelerar o desenvolvimento backend com Python. Fornece uma base sólida baseada nos princípios de Clean Architecture e Domain-Driven Design (DDD), aproveitando Python Generics (PEP 695) para maximizar reuso de código e type safety.


### Por que usar este framework?

| Problema | Solução |
|----------|---------|
| Boilerplate repetitivo | CRUD genérico com apenas 3 arquivos |
| Falta de type safety | Generics PEP 695 com suporte completo de IDE |
| Segurança complexa | JWT + RBAC + Rate Limiting prontos |
| Observabilidade difícil | OpenTelemetry + structlog integrados |
| Testes trabalhosos | 200+ testes property-based inclusos |
| Deploy complicado | Docker, K8s, Terraform, Serverless prontos |

---

## Características

### Core Features

- **CRUD Zero Boilerplate** - Crie endpoints REST completos com apenas 3 arquivos: entidade, use case e router
- **Generics Type-Safe** - `IRepository[T]`, `BaseUseCase[T]`, `GenericCRUDRouter[T]` com suporte completo de IDE
- **Clean Architecture** - Separação clara de responsabilidades em 5 camadas
- **Domain-Driven Design** - Entidades, Value Objects, Aggregates, Specifications, Domain Events

### Segurança

- **Autenticação JWT** - Access tokens (30min) + Refresh tokens (7 dias)
- **RBAC** - Role-Based Access Control com composição de permissões
- **Rate Limiting** - slowapi com limites configuráveis por endpoint
- **Security Headers** - CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Password Policy** - Argon2 hashing + política configurável
- **Token Revocation** - Blacklist via Redis

### Resiliência

- **Circuit Breaker** - Proteção contra falhas em cascata
- **Retry Pattern** - Backoff exponencial com jitter
- **Bulkhead** - Isolamento de recursos
- **Timeout** - Controle de tempo de execução

### Observabilidade

- **Tracing** - OpenTelemetry com exportação OTLP
- **Metrics** - Prometheus endpoint `/metrics`
- **Logging** - structlog com formato JSON/ECS
- **Correlation ID** - Rastreamento de requests

### Infraestrutura

- **PostgreSQL** - SQLAlchemy 2.0 + Alembic migrations
- **Redis** - Cache + Token storage
- **Elasticsearch** - Full-text search
- **Kafka** - Event streaming
- **MinIO/S3** - Object storage
- **RabbitMQ** - Background tasks

---

## Arquitetura

O projeto implementa Clean Architecture com 5 camadas principais:

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACE LAYER                          │
│  (FastAPI Routers, Middleware, GraphQL, WebSocket, Versioning)  │
├─────────────────────────────────────────────────────────────────┤
│                       APPLICATION LAYER                         │
│    (Use Cases, Commands, Queries, DTOs, Mappers, Services)      │
├─────────────────────────────────────────────────────────────────┤
│                         DOMAIN LAYER                            │
│   (Entities, Value Objects, Aggregates, Specifications, Events) │
├─────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE LAYER                       │
│  (Database, Cache, Messaging, Storage, Auth, Observability)     │
├─────────────────────────────────────────────────────────────────┤
│                          CORE LAYER                             │
│     (Configuration, DI Container, Protocols, Base Types)        │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

```
Client → Middleware → Router → Use Case → Domain → Infrastructure → Database
                                   ↓
                              Domain Events → Event Bus → Handlers
```

---

## Estrutura do Projeto

```
python-api-base/
├── src/                           # Código fonte principal
│   ├── core/                      # Kernel da aplicação
│   │   ├── base/                  # Classes base abstratas (CQRS, Events, Repository)
│   │   ├── config/                # Configurações (Settings, Security, Database)
│   │   ├── di/                    # Container de Injeção de Dependência
│   │   ├── errors/                # Exception handlers RFC 7807
│   │   ├── protocols/             # Interfaces/Protocolos (Repository, Entity)
│   │   ├── shared/                # Utilitários (Logging, Caching)
│   │   └── types/                 # Type aliases e definições
│   │
│   ├── domain/                    # Camada de Domínio (DDD)
│   │   ├── common/                # Specification pattern, Value Objects base
│   │   ├── users/                 # Bounded Context: Usuários
│   │   └── examples/              # Bounded Context: Exemplos (Item, Pedido)
│   │
│   ├── application/               # Camada de Aplicação
│   │   ├── common/                # CQRS, Middleware, Batch operations
│   │   ├── services/              # Feature Flags, File Upload, Multitenancy
│   │   ├── users/                 # Use cases de usuários (Commands, Queries)
│   │   └── examples/              # Use
#   │
│   ├── i Destaqncture/       frastr Camada de Infraestrutura
│  u#aisudit/        Audit trail
│   │   ├── auth/                  # JWT, Pard Policy, Token Store
|-------├── cache/             # Redis,providers
│   db/              # SQLAlchemy,ilder, Migration
 ca │   ├── elasticsearch/         # Search engine
│   │   ├──ses d--|                # Event streamingção de permissões |
| **Pro# o ObjecProdução** | Rate limiting, headers de segurança, request tracing, health checks inclusos |
| **Padrões de Resiliência** | Circuit breaker, retry com backoff exponencial, bulkhead, timeout |
| **Observt spidade** | OpenTelema, metrics), structlog (JSON), PromethK Stack |
| **CQRS & Evecing** | Separandos/queries, doments, event store
| **200+ s** | T unitários, property-based (Hyps) e load tests (k

---

## Característic
│  ─ prometh │ra nteus/        rvabilPrometheus metrics
│   itre Featuresda de Interface
│   │   ├── errors/             # Error hHTTP
│   │   ├── graphql/       # Grap resolv
ite │   ├── mc Sepan-e/            # HTTP middlewaDrivtack
│   en  ├── routes/                # Route definitions raçãgn** - Modelago crica densív
- **Ty  ├── pe/                    # API v1elafetyouteníenerics PEP 695 pmáxima segança de tipourara vel e om entidades, val dts, aes
│   │   ├──- 2/ **SOLIDdency       # API v2 endpoints
│   │   └── versioning/   InjecCon # API versioning strategiestner IoC compenlmenno asyncio
    │
│   └comtedency   -inj             # Application entry point
│
├──ecests/      tor               # Tes
│   ├── uni              # Testes unitários
│   e, Argtegration/        on     # Testes de integração
│   ├── properties/                # Property-based tests (200+ a2 hashing)dis
*   ├── e2e/   *Sec              Headers** -end tests
│   ├── performance/     CSP, HSTS,# Load test Xme-O
│   └── factories/              ptionTest factories (P cyfactoronticm sanitiza vomática
- **P2 ção autcon** - Redaçãotwapimática de dadossíveis em lo
-── docs/               **         # Incumentação
│   ├── adr/                     putsArchitecture D, erion Records
│bation api/                       # Documenta**  de API
│ -use  architecture/ co           # Documentm ao de arquitetura
│   ├── guides/                    # Gui ant-Tyso
│   ├── infrastructupe-Oion        # DocsptX-Cnfrao
│   ├── layers/                 # Docs r camada
│   ├── operations/    # Runbooks e operações
│   └── testing/           # Gus
│
├── deployments/                   # Configurações de depl
- # ├── docker Infraest            # Docker Compose files
│   ├── helm/             rutur    # Helm charts
│   ├── k8s/                       # Kubernetes manifests
│   ├─a**nt Limiss/                ting** -mbda, Vercel
│   └── terr Pro                 nfrastructure Code
│
├─ts/                  # Scripts utilitários
├── alembic/                  # Datamigrations
- deTostgexample                   # Template de configuração
├── pyproject.toml             reSQL**ependências e co ** - ação
├── MaFullle                       # Coman-texte des sealvimento
└── READMsagd    ing         # Este arquivo
```

- **MinIO/Srch - Objeground taskct sformance (opcRPC
tação OTLP
- **Metrics- Prometheus endpointo de req métricas cupés de servirobes
-stomorrelation ID*i Rastreamen
#--
──────────────┤
│                         DOMAIN LAYER                            │
│   (Entities, Value Objects, Aggregates, Specifications, Events) │
├─────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE LAYER                       │
│  (Database, Cache, Messaging, Storage, Auth, Observability)     │
├─────────────────────────────────────────────────────────────────┤
│                          CORE LAYER                             │
│     (Configuration, DI Container, Protocols, Base Types)        │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

```
Client Request
     │
     ▼
┌─────────────┐
│  Middleware │ ─── Auth, Rate Limit, Logging, Security Headers
└─────────────┘
     │
     ▼
┌─────────────┐
│   Router    │ ─── Validação de entrada (Pydantic)
└─────────────┘
     │
     ▼
┌─────────────┐
│  Use Case   │ ─── Orquestração de lógica de negócio
└─────────────┘
     │
     ▼
┌─────────────┐
│   Domain    │ ─── Regras de negócio, validações
└─────────────┘
     │
     ▼
┌─────────────┐
│Infrastructure│ ─── Persistência, cache, eventos
└─────────────┘
     │
     ▼
  Response
```


## ArquiteturaRters, MiddlewaFACE LAYERL, WebSocket, Ver───       │
──│──┤es, Com───────────────man──────────────ds, Queries, DTOs, Mappers, Services)      │

│                 sioning) LICATION LAYE │                                 │
│  (FastAP────────I Rou─────────────────────────────────
```─────────────       INTE────────────────────┐
                
┌────────────────────────────────
 **Health Check## Ob Liveness e vabilidadeJSON/ECS
*Structuributed Tracing*red LognTelemetry com exging** - structlogom formato 
- *
- **ScyllaDB** - NoSQL para altorage para he, token-regation
- **RabbitMQ** -  **Ka Banco  Event streaming e mes, rate limiting, distributed locks
- **Ede dados pken Real com SQLAlchaitioaon+ SQLModel
- **Red** - Blacklist via Rençaol com composiçãmissõconfigurável (comprimento, complexidades
- **Password Policy** - Validação 
ccess tokens (30minesh tokens (7 dias)
-BAC** - Role-Based A
- **JWTn*uthentication** - A*ait** - Tota -  Principles** - Código mggregatomínilara de sabilidades em ca
- **Clea─ interface/      # Cama           y/  ─ rbac/                  # Redis client            Bulkhead
│   │
│   ├─│   ├── scylladb/              # File storage   # Scyllon
│   │   └── tasks/          aDB    # Background tasks (RabbitMQ)
│   /Cassandra
│   le-Bas─ storage/      ed Access   # Tel
│   │   ├── resilience/            # Circuit Breaker, Retry,  ├── redis/  etry, Logging, Metrics
│├─
│   │ ---Complnio/              e| tokens, revoJWTRedis, C com compoRBA cosh m access/refta** ----sitory----|e** | Crie[T]`, `B endT case[T]`, `omnericCRorteompleto de cUDRouter[T]` com pletapenas 3 arqos: entidade,e router |
|e**Autenticação nerics Type-Safe
| **CRUD Zero Boilerple exemplurso | Descriçã
---


## Estrutura do Projeto

```
python-api-base/
├── src/                           # Código fonte principal
│   ├── core/                      # Kernel da aplicação
│   │   ├── base/                  # Classes base abstratas (CQRS, Domain, Events, Repository)
│   │   ├── config/                # Configurações (Settings, Database, Security, Observability)
│   │   ├── di/                    # Container de Injeção de Dependência
│   │   ├── errors/                # Exception handlers RFC 7807
│   │   ├── protocols/             # Interfaces/Protocolos (Repository, Entity, Mapper)
│   │   ├── shared/                # Utilitários compartilhados (Logging, Caching)
│   │   └── types/                 # Type aliases e definições
│   │
│   ├── domain/                    # Camada de Domínio (DDD)
│   │   ├── common/                # Specification pattern, Value Objects base
│   │   ├── users/                 # Bounded Context: Usuários
│   │   └── examples/              # Bounded Context: Exemplos (Item, Pedido)
│   │
│   ├── application/               # Camada de Aplicação
│   │   ├── common/                # CQRS, Middleware, Batch operations, Export
│   │   ├── services/              # Cross-cutting services (Feature Flags, File Upload, Multitenancy)
│   │   ├── users/                 # Use cases de usuários (Commands, Queries)
│   │   └── examples/              # Use cases de exemplos
│   │
│   ├── infrastructure/            # Camada de Infraestrutura
│   │   ├── audit/                 # Audit trail
│   │   ├── auth/                  # Autenticação (JWT, OAuth, Password Policy, Token Store)
│   │   ├── cache/                 # Cache (Redis, Memory, Decorators)
│   │   ├── db/                    # Database (Session, Repositories, Query Builder, Migrations)
│   │   ├── elasticsearch/         # Search engine
│   │   ├── kafka/                 # Event streaming
│   │   ├── minio/                 # Object storage
│   │   ├── messaging/             # Messaging (AsyncAPI, Brokers, DLQ, Notifications)
│   │   ├── multitenancy/          # Multi-tenant support
│   │   ├── observability/         # Telemetry, Logging, Metrics, Tracing
│   │   ├── prometheus/            # Prometheus metrics
│   │   ├── ratelimit/             # Rate limiting
│   │   ├── rbac/                  # Role-Based Access Control
│   │   ├── redis/                 # Redis client
│   │   ├── resilience/            # Circuit Breaker, Retry, Bulkhead, Timeout
│   │   ├── scylladb/              # ScyllaDB/Cassandra
│   │   ├── security/              # Field encryption, Password hashers
│   │   ├── storage/               # File storage abstraction
│   │   └── tasks/                 # Background tasks (RabbitMQ)
│   │
│   ├── interface/                 # Camada de Interface
│   │   ├── errors/                # Error handlers HTTP
│   │   ├── graphql/               # GraphQL schema (Strawberry)
│   │   ├── middleware/            # HTTP middleware (Security, Logging, Request)
│   │   ├── routes/                # Route definitions
│   │   ├── v1/                    # API v1 endpoints
│   │   ├── v2/                    # API v2 endpoints
│   │   └── versioning/            # API versioning strategies
│   │
│   └── main.py                    # Application entry point
│
├── tests/                         # Testes
│   ├── unit/                      # Testes unitários
│   ├── integration/               # Testes de integração
│   ├── properties/                # Property-based tests (Hypothesis)
│   ├── e2e/                       # End-to-end tests
│   ├── performance/               # Load tests (k6)
│   └── factories/                 # Test factories (Polyfactory)
│
├── docs/                          # Documentação
│   ├── adr/                       # Architecture Decision Records
│   ├── api/                       # API documentation
│   ├── architecture/              # Architecture docs
│   ├── guides/                    # User guides
│   ├── infrastructure/            # Infrastructure docs
│   ├── layers/                    # Layer documentation
│   ├── operations/                # Operations runbooks
│   └── testing/                   # Testing guides
│
├── deployments/                   # Configurações de deploy
│   ├── docker/                    # Docker Compose files
│   ├── helm/                      # Helm charts
│   ├── k8s/                       # Kubernetes manifests
│   ├── serverless/                # AWS Lambda, Vercel
│   └── terraform/                 # Infrastructure as Code
│
├── scripts/                       # Scripts utilitários
├── alembic/                       # Database migrations
├── .env.example                   # Template de configuração
├── pyproject.toml                 # Dependências e configuração
├── Makefile                       # Comandos de automação
└── README.md                      # Este arquivo
```


---

## Início Rápido

### Pré-requisitos

| Software | Versão | Obrigatório |
|----------|--------|-------------|
| Python | 3.12+ | ✅ |
| uv | latest | Recomendado |
| Docker | 24+ | ✅ |
| Docker Compose | 2.0+ | ✅ |

### 1. Clonar e Instalar

```bash
# Clonar repositório
git clone https://github.com/example/python-api-base.git
cd python-api-base

# Instalar com uv (recomendado)
uv sync --dev

# Ou com pip
pip install -e ".[dev]"
```

### 2. Configurar Ambiente

```bash
# Copiar template de configuração
cp .env.example .env

# Gerar chave secreta (OBRIGATÓRIO)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Editar .env e configurar SECURITY__SECRET_KEY
```

### 3. Iniciar Infraestrutura

```bash
# Iniciar PostgreSQL e Redis
docker compose -f deployments/docker/docker-compose.base.yml up -d postgres redis

# Ou usar Makefile
make setup-db
```

### 4. Executar Migrations

```bash
# Aplicar migrations
uv run alembic upgrade head

# Ou usar Makefile
make migrate
```

### 5. Iniciar API

```bash
# Desenvolvimento com hot reload
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Ou usar Makefile
make run
```

### 6. Verificar Instalação

```bash
# Health check
curl http://localhost:8000/health/live
# Resposta: {"status": "healthy"}

# Documentação
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Endpoints Disponíveis

| Endpoint | Descrição |
|----------|-----------|
| `http://localhost:8000` | Base da API |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/health/live` | Liveness Check |
| `http://localhost:8000/health/ready` | Readiness Check |
| `http://localhost:8000/metrics` | Prometheus Metrics |
| `http://localhost:8000/graphql` | GraphQL Playground (se habilitado) |


---

## Módulos

### Core Layer (`src/core/`)

| Módulo | Descrição | Exports Principais |
|--------|-----------|-------------------|
| `core.config` | Configurações centralizadas | `Settings`, `get_settings`, `DatabaseSettings`, `SecuritySettings` |
| `core.protocols` | Interfaces/Protocolos | `AsyncRepository`, `Entity`, `Mapper`, `UnitOfWork` |
| `core.di` | Container de DI | `Container`, `get_container` |
| `core.errors` | Exception handlers | `AppException`, `ValidationError`, `NotFoundError` |
| `core.types` | Type definitions | `EntityId`, `JsonDict`, `Result` |
| `core.shared` | Utilitários | `get_logger`, `cached` |

### Domain Layer (`src/domain/`)

| Módulo | Descrição | Componentes |
|--------|-----------|-------------|
| `domain.common` | Componentes compartilhados | `Specification`, `ValueObject`, `DomainEvent` |
| `domain.users` | Bounded Context Usuários | `User`, `Email`, `Password`, `IUserRepository` |
| `domain.examples` | Exemplos de implementação | `Item`, `Pedido` |

### Application Layer (`src/application/`)

| Módulo | Descrição | Componentes |
|--------|-----------|-------------|
| `application.common.cqrs` | CQRS Pattern | `Command`, `Query`, `CommandBus`, `QueryBus` |
| `application.common.batch` | Operações em lote | `BatchProcessor`, `BatchResult` |
| `application.common.export` | Exportação de dados | `DataExporter`, `ExportFormat` |
| `application.services` | Serviços cross-cutting | `FeatureFlagService`, `FileUploadService`, `TenantService` |
| `application.users` | Use cases de usuários | `CreateUserCommand`, `GetUserQuery`, `UserDTO` |

### Infrastructure Layer (`src/infrastructure/`)

| Módulo | Descrição | Componentes |
|--------|-----------|-------------|
| `infrastructure.auth` | Autenticação | `JWTService`, `PasswordPolicy`, `TokenStore` |
| `infrastructure.cache` | Cache | `CacheProvider`, `RedisCacheProvider`, `@cached` |
| `infrastructure.db` | Database | `AsyncSession`, `Repository`, `QueryBuilder` |
| `infrastructure.resilience` | Resiliência | `CircuitBreaker`, `Retry`, `Bulkhead`, `Timeout` |
| `infrastructure.observability` | Observabilidade | `TelemetryService`, `LoggingMiddleware` |
| `infrastructure.rbac` | Autorização | `RBACChecker`, `Permission`, `Role` |
| `infrastructure.kafka` | Event streaming | `KafkaProducer`, `KafkaConsumer` |
| `infrastructure.elasticsearch` | Search | `ElasticsearchRepository`, `SearchQuery` |
| `infrastructure.minio` | Object storage | `MinIOClient`, `FileUploadHandler` |
| `infrastructure.redis` | Redis client | `RedisClient`, `DistributedLock` |

### Interface Layer (`src/interface/`)

| Módulo | Descrição | Componentes |
|--------|-----------|-------------|
| `interface.v1` | API v1 endpoints | `users_router`, `items_router`, `health_router` |
| `interface.v2` | API v2 endpoints | `examples_router` |
| `interface.middleware` | HTTP middleware | `SecurityHeadersMiddleware`, `LoggingMiddleware` |
| `interface.graphql` | GraphQL | `schema`, `resolvers`, `dataloader` |
| `interface.errors` | Error handlers | `exception_handler`, `validation_handler` |


---

## Padrões de Design

### Specification Pattern

Encapsula regras de negócio em objetos composáveis.

```python
from domain.common.specification import equals, greater_than, is_null

# Specifications individuais
active_users = equals("is_active", True)
premium_users = equals("subscription", "premium")
not_deleted = is_null("deleted_at")

# Composição com AND/OR
target_users = active_users.and_spec(premium_users).and_spec(not_deleted)

# Uso com SQLAlchemy
query = select(User).where(target_users.to_sql_condition(User))
```

**Operadores disponíveis:** `EQ`, `NE`, `GT`, `GE`, `LT`, `LE`, `CONTAINS`, `STARTS_WITH`, `IN`, `IS_NULL`, `IS_NOT_NULL`

### CQRS Pattern

Separação de operações de leitura e escrita.

```python
from application.common.cqrs import Command, Query
from core.types import Result

# Command (Escrita)
@dataclass
class CreateUserCommand(Command[User]):
    email: str
    name: str
    password: str

    async def execute(self, repository: IUserRepository) -> Result[User, str]:
        if await repository.exists_by_email(self.email):
            return Err("Email already exists")
        user = User(email=self.email, name=self.name)
        return Ok(await repository.create(user))

# Query (Leitura)
@dataclass
class GetUserQuery(Query[UserDTO | None]):
    user_id: str
    cacheable: bool = True

    async def execute(self, repository: IUserRepository) -> UserDTO | None:
        user = await repository.get(self.user_id)
        return UserMapper.to_dto(user) if user else None
```

### Repository Pattern

Abstrai o acesso a dados através de interfaces.

```python
# Interface (Domain)
class IUserRepository(AsyncRepository[User, str], Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def exists_by_email(self, email: str) -> bool: ...

# Implementação (Infrastructure)
class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, id: str) -> User | None:
        return await self._session.get(UserModel, id)

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user
```

### Resilience Patterns

```python
from infrastructure.resilience import CircuitBreaker, Retry, Bulkhead, Timeout

# Circuit Breaker - Proteção contra falhas em cascata
circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
result = await circuit.execute(lambda: external_api.call())

# Retry com Exponential Backoff
retry = Retry(max_attempts=3, base_delay=1.0, exponential_base=2.0)
result = await retry.execute(lambda: flaky_service.call())

# Bulkhead - Limitador de concorrência
bulkhead = Bulkhead(max_concurrent=10, max_wait=5.0)
result = await bulkhead.execute(lambda: expensive_operation())

# Timeout
timeout = Timeout(timeout=30.0)
result = await timeout.execute(lambda: slow_operation())
```


---

## Autenticação e Autorização

### JWT Authentication

```python
from infrastructure.auth.jwt import JWTService

jwt_service = JWTService(secret_key="...", algorithm="HS256")

# Criar tokens
access_token = jwt_service.create_access_token(
    user_id="123",
    roles=["admin"],
    expires_minutes=30
)
refresh_token = jwt_service.create_refresh_token(user_id="123")

# Validar token
payload = jwt_service.verify_token(access_token)
# payload: {"sub": "123", "roles": ["admin"], "exp": ..., "jti": "..."}
```

### Token Revocation

```python
from infrastructure.auth.token_store import TokenStore

token_store = TokenStore(redis_client)

# Revogar token (logout)
await token_store.revoke_token(token_jti, expires_at)

# Verificar se está revogado
is_revoked = await token_store.is_revoked(token_jti)

# Revogar todos os tokens de um usuário
await token_store.revoke_all_user_tokens(user_id)
```

### RBAC (Role-Based Access Control)

```python
from infrastructure.rbac import RBACChecker, Role, Permission

# Definir roles com permissões
admin_role = Role(
    name="admin",
    permissions=[
        Permission(resource="users", action="read"),
        Permission(resource="users", action="write"),
        Permission(resource="users", action="delete"),
    ]
)

editor_role = Role(
    name="editor",
    permissions=[
        Permission(resource="posts", action="read"),
        Permission(resource="posts", action="write"),
    ]
)

# Verificar permissão
rbac = RBACChecker()
rbac.register_role(admin_role)
rbac.register_role(editor_role)

has_access = rbac.has_permission(
    user_roles=["editor"],
    resource="posts",
    action="write"
)  # True
```

### Password Policy

```python
from infrastructure.auth.password_policy import PasswordPolicy

policy = PasswordPolicy(
    min_length=12,
    require_uppercase=True,
    require_lowercase=True,
    require_digit=True,
    require_special=True,
    max_repeated_chars=3,
)

result = policy.validate("MyP@ssw0rd123")
if not result.is_valid:
    print(result.errors)  # Lista de erros de validação
```

### Uso em Rotas

```python
from fastapi import Depends
from interface.dependencies import get_current_user, require_permission

@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("users", "read"))
):
    return await user_service.list_all()

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("users", "delete"))
):
    return await user_service.delete(user_id)
```


---

## Recursos Avançados

### Caching

```python
from infrastructure.cache import cached, RedisCacheProvider

# Decorator simples
@cached(ttl=300)
async def get_user(user_id: str) -> User:
    return await repository.get(user_id)

# Com key builder customizado
@cached(ttl=60, key_builder=lambda **kw: f"user:{kw['user_id']}")
async def get_user_profile(user_id: str) -> UserProfile:
    return await profile_service.get(user_id)

# Provider direto
cache = RedisCacheProvider(redis_client)
await cache.set("key", value, ttl=300)
value = await cache.get("key")
await cache.delete("key")
await cache.clear_pattern("user:*")
```

### Domain Events

```python
from infrastructure.messaging import EventBus, DomainEvent

# Definir evento
@dataclass
class UserCreatedEvent(DomainEvent):
    user_id: str
    email: str
    created_at: datetime

# Subscribe
@event_bus.subscribe("user.created")
async def handle_user_created(event: UserCreatedEvent):
    await send_welcome_email(event.email)
    await create_audit_log(event)

# Publish
await event_bus.publish(UserCreatedEvent(
    user_id="123",
    email="user@example.com",
    created_at=datetime.utcnow()
))
```

### Tracing (OpenTelemetry)

```python
from infrastructure.observability.telemetry import traced

@traced(name="process_payment", attributes={"provider": "stripe"})
async def process_payment(order_id: str, amount: float) -> bool:
    # Span criado automaticamente
    # Exceções registradas como eventos
    return await stripe.charge(order_id, amount)
```

### Structured Logging

```python
from core.shared.logging import get_logger

logger = get_logger(__name__)

logger.info(
    "order_processed",
    order_id=order_id,
    total=order.total,
    items_count=len(order.items),
    customer_id=order.customer_id,
)
# Output JSON: {"event": "order_processed", "order_id": "...", ...}
```

### Feature Flags

```python
from infrastructure.feature_flags import FeatureFlagService

flags = FeatureFlagService()

# Verificar flag
if await flags.is_enabled("new_checkout_flow", user_context):
    return await new_checkout(order)
else:
    return await legacy_checkout(order)

# Com fallback
result = await flags.get_value("max_items_per_order", default=10)
```

### File Upload

```python
from infrastructure.storage import FileUploadHandler, FileValidator

validator = FileValidator(
    max_size=10 * 1024 * 1024,  # 10MB
    allowed_extensions=["jpg", "png", "pdf"],
    allowed_mimetypes=["image/jpeg", "image/png", "application/pdf"],
)

handler = FileUploadHandler(storage_provider, validator)

# Upload
file_info = await handler.upload(file, folder="documents")
# file_info: FileInfo(id="...", url="...", size=..., mimetype="...")

# Download
content = await handler.download(file_info.id)
```

### Multitenancy

```python
from infrastructure.multitenancy import TenantContext, tenant_middleware

# Middleware extrai tenant do header/subdomain
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    tenant_id = extract_tenant(request)
    with TenantContext(tenant_id):
        return await call_next(request)

# Uso em queries
async def get_users():
    tenant_id = TenantContext.current()
    return await repository.get_by_tenant(tenant_id)
```


---

## Configuração

### Variáveis de Ambiente

#### Aplicação

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `APP_NAME` | string | "My API" | Nome da aplicação |
| `DEBUG` | bool | false | Modo debug (NUNCA true em produção) |
| `VERSION` | string | "0.1.0" | Versão da API |
| `API_PREFIX` | string | "/api/v1" | Prefixo das rotas |

#### Database

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `DATABASE__URL` | string | - | Connection string PostgreSQL |
| `DATABASE__POOL_SIZE` | int | 10 | Tamanho do pool de conexões |
| `DATABASE__MAX_OVERFLOW` | int | 20 | Conexões extras permitidas |
| `DATABASE__ECHO` | bool | false | Log de queries SQL |

#### Security

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `SECURITY__SECRET_KEY` | string | - | Chave JWT (mín 32 chars) **OBRIGATÓRIO** |
| `SECURITY__CORS_ORIGINS` | list | ["*"] | Origens CORS permitidas |
| `SECURITY__RATE_LIMIT` | string | "100/minute" | Rate limit |
| `SECURITY__ALGORITHM` | string | "HS256" | Algoritmo JWT |
| `SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES` | int | 30 | Expiração access token |
| `SECURITY__REFRESH_TOKEN_EXPIRE_DAYS` | int | 7 | Expiração refresh token |

#### Redis

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `REDIS__URL` | string | "redis://localhost:6379/0" | URL Redis |
| `REDIS__ENABLED` | bool | false | Habilitar Redis |
| `REDIS__TOKEN_TTL` | int | 604800 | TTL de tokens (segundos) |

#### Observability

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__LOG_LEVEL` | string | "INFO" | Nível de log |
| `OBSERVABILITY__LOG_FORMAT` | string | "json" | Formato (json/console) |
| `OBSERVABILITY__OTLP_ENDPOINT` | string | null | Endpoint OpenTelemetry |
| `OBSERVABILITY__SERVICE_NAME` | string | "python-api-base" | Nome do serviço |
| `OBSERVABILITY__PROMETHEUS_ENABLED` | bool | true | Habilitar Prometheus |
| `OBSERVABILITY__KAFKA_ENABLED` | bool | false | Habilitar Kafka |
| `OBSERVABILITY__ELASTICSEARCH_ENABLED` | bool | false | Habilitar Elasticsearch |

### Exemplo de .env

```bash
# Application
APP_NAME="My API"
DEBUG=false
VERSION="1.0.0"

# Database
DATABASE__URL=postgresql+asyncpg://user:password@localhost:5432/mydb
DATABASE__POOL_SIZE=20

# Security (OBRIGATÓRIO)
SECURITY__SECRET_KEY=your-super-secret-key-at-least-32-characters-long
SECURITY__CORS_ORIGINS=["https://app.example.com"]
SECURITY__RATE_LIMIT=100/minute

# Redis
REDIS__URL=redis://localhost:6379/0
REDIS__ENABLED=true

# Observability
OBSERVABILITY__LOG_LEVEL=INFO
OBSERVABILITY__LOG_FORMAT=json
OBSERVABILITY__OTLP_ENDPOINT=http://localhost:4317
OBSERVABILITY__PROMETHEUS_ENABLED=true
```

### Gerar Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```


---

## Testes

### Estrutura de Testes

```
tests/
├── conftest.py              # Fixtures compartilhadas
├── factories/               # Test factories (Polyfactory, Hypothesis strategies)
│   ├── entity_factory.py
│   ├── hypothesis_strategies.py
│   └── mock_repository.py
├── unit/                    # Testes unitários (isolados, sem I/O)
│   ├── application/
│   ├── core/
│   ├── domain/
│   ├── infrastructure/
│   └── interface/
├── integration/             # Testes de integração (com banco, Redis, etc)
│   ├── db/
│   ├── infrastructure/
│   └── interface/
├── properties/              # Property-based tests (Hypothesis) - 200+ arquivos
├── e2e/                     # End-to-end tests
│   └── api/
└── performance/             # Load tests (k6)
    ├── smoke.js
    └── stress.js
```

### Executando Testes

```bash
# Todos os testes
uv run pytest

# Com cobertura
uv run pytest --cov=src --cov-report=html --cov-report=term

# Por tipo
uv run pytest tests/unit/           # Unitários
uv run pytest tests/integration/    # Integração
uv run pytest tests/properties/     # Property-based
uv run pytest tests/e2e/            # End-to-end

# Teste específico
uv run pytest tests/unit/domain/users/test_user.py::TestUser::test_create

# Por marcador
uv run pytest -m "unit"
uv run pytest -m "integration"
uv run pytest -m "property"

# Com verbose
uv run pytest -v

# Paralelismo
uv run pytest -n auto
```

### Property-Based Tests (Hypothesis)

O projeto inclui 200+ arquivos de testes property-based cobrindo:

| Categoria | Exemplos |
|-----------|----------|
| **JWT** | Token round-trip, validação, expiração |
| **RBAC** | Permission composition, role inheritance |
| **Repository** | CRUD consistency, soft delete |
| **Cache** | Invalidation, TTL, serialization |
| **Security** | Headers presence, sanitization |
| **Errors** | RFC 7807 format, status codes |
| **Resilience** | Circuit breaker states, retry backoff |
| **Specification** | Composition laws, SQL conversion |

```python
# Exemplo de property test
from hypothesis import given, strategies as st

@given(st.emails())
def test_email_validation_accepts_valid_emails(email: str):
    """Qualquer email válido deve ser aceito."""
    result = validate_email(email)
    assert result.is_valid

@given(st.integers(), st.integers())
def test_specification_and_is_commutative(a: int, b: int):
    """AND composition deve ser comutativa."""
    spec1 = equals("value", a)
    spec2 = equals("value", b)
    obj = {"value": a}
    assert spec1.and_spec(spec2).is_satisfied_by(obj) == \
           spec2.and_spec(spec1).is_satisfied_by(obj)
```

### Load Tests (k6)

```bash
# Instalar k6: https://k6.io/docs/get-started/installation/

# Smoke test (verificação básica)
k6 run tests/performance/smoke.js

# Stress test (encontrar limites)
k6 run tests/performance/stress.js

# Com URL customizada
k6 run -e BASE_URL=http://api.example.com tests/performance/smoke.js
```

### Cobertura

- **Mínimo exigido:** 80%
- **Branch coverage:** 75%

```bash
# Gerar relatório HTML
uv run pytest --cov=src --cov-report=html

# Abrir relatório
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```


---

## Deploy

### Opções de Deploy

O projeto suporta múltiplas estratégias de deploy:

| Método | Localização | Descrição |
|--------|-------------|-----------|
| **Docker** | `deployments/docker/` | Docker Compose para dev/staging/prod |
| **Kubernetes** | `deployments/k8s/` | Manifests K8s com Kustomize |
| **Helm** | `deployments/helm/` | Helm charts para K8s |
| **Terraform** | `deployments/terraform/` | IaC para AWS/GCP/Azure |
| **Serverless** | `deployments/serverless/` | AWS Lambda, Vercel |

### Docker

```bash
# Desenvolvimento
docker compose -f deployments/docker/docker-compose.base.yml \
               -f deployments/docker/docker-compose.dev.yml up -d

# Produção
docker compose -f deployments/docker/docker-compose.base.yml \
               -f deployments/docker/docker-compose.production.yml up -d

# Build da imagem
docker build -t my-api:latest -f deployments/docker/dockerfiles/Dockerfile.prod .
```

### Kubernetes

```bash
# Aplicar manifests
kubectl apply -k deployments/k8s/base/

# Com overlay de ambiente
kubectl apply -k deployments/k8s/overlays/production/
```

### Helm

```bash
# Instalar chart
helm install my-api deployments/helm/api/ \
  --namespace my-api \
  --create-namespace \
  --values deployments/helm/api/values-production.yaml
```

### Terraform

```bash
cd deployments/terraform

# Inicializar
terraform init

# Planejar
terraform plan -var-file=environments/production.tfvars

# Aplicar
terraform apply -var-file=environments/production.tfvars
```


---

## Comandos Úteis

### Makefile

O projeto inclui um Makefile completo para automação:

```bash
# Setup inicial completo
make setup

# Desenvolvimento
make run              # Iniciar servidor dev
make run-prod         # Iniciar servidor produção

# Database
make migrate          # Aplicar migrations
make migrate-down     # Rollback última migration
make migrate-create msg="add users table"  # Criar migration

# Testes
make test             # Todos os testes
make test-unit        # Unitários
make test-integration # Integração
make test-property    # Property-based
make test-cov         # Com cobertura

# Qualidade de código
make lint             # Verificar lint (ruff)
make lint-fix         # Corrigir lint
make format           # Formatar código
make type-check       # Type check (mypy)
make check            # Todas as verificações

# Segurança
make security         # Scan de segurança (bandit)
make security-full    # Scan completo + secrets

# Docker
make docker-up        # Iniciar serviços
make docker-down      # Parar serviços
make docker-logs      # Ver logs
make docker-rebuild   # Rebuild imagens

# Documentação
make docs-serve       # Servir docs localmente
make docs-build       # Build docs

# Limpeza
make clean            # Limpar arquivos temporários
make clean-all        # Limpar tudo incluindo venv

# Utilitários
make generate-secret  # Gerar secret key
make health           # Verificar saúde do sistema
make validate         # Validar configurações
```

### Scripts Disponíveis

```bash
# Validar documentação
python scripts/validate_docs.py

# Validar configurações
python scripts/validate-config.py
python scripts/validate-config.py --strict  # Modo estrito
python scripts/validate-config.py --fix     # Auto-fix

# Seed de dados de exemplo
python scripts/seed_examples.py
```

### CLI

```bash
# Comandos via CLI
uv run api-cli --help
```


---

## Stack Tecnológica

### Core

| Categoria | Tecnologia | Versão |
|-----------|------------|--------|
| Linguagem | Python | 3.12+ |
| Framework Web | FastAPI | 0.115+ |
| Validação | Pydantic | 2.9+ |
| ORM | SQLAlchemy + SQLModel | 2.0+ |
| Migrations | Alembic | 1.14+ |
| DI Container | dependency-injector | 4.42+ |

### Database & Cache

| Categoria | Tecnologia | Uso |
|-----------|------------|-----|
| Database | PostgreSQL | Banco principal |
| ORM Async | asyncpg | Driver async PostgreSQL |
| Cache | Redis | Cache, tokens, rate limit |
| Search | Elasticsearch | Full-text search |
| NoSQL | ScyllaDB | Alta performance (opcional) |

### Messaging & Events

| Categoria | Tecnologia | Uso |
|-----------|------------|-----|
| Event Streaming | Kafka (aiokafka) | Domain events |
| Message Queue | RabbitMQ | Background tasks |
| Object Storage | MinIO | File uploads |

### Observabilidade

| Categoria | Tecnologia | Uso |
|-----------|------------|-----|
| Logging | structlog | Structured JSON logs |
| Tracing | OpenTelemetry | Distributed tracing |
| Metrics | Prometheus | Métricas customizadas |
| Log Aggregation | Elasticsearch | Centralização de logs |

### Segurança

| Categoria | Tecnologia | Uso |
|-----------|------------|-----|
| Rate Limiting | slowapi | Proteção contra abuse |
| Password Hashing | passlib (Argon2) | Hash seguro de senhas |
| JWT | python-jose | Tokens de autenticação |
| Encryption | cryptography | Criptografia de campos |

### Testes

| Categoria | Tecnologia | Uso |
|-----------|------------|-----|
| Test Framework | pytest | Execução de testes |
| Async Tests | pytest-asyncio | Testes assíncronos |
| Property Tests | Hypothesis | Property-based testing |
| Factories | polyfactory | Geração de dados de teste |
| Mocking | respx | Mock de HTTP requests |
| Load Tests | k6 | Testes de carga |
| Coverage | pytest-cov | Cobertura de código |

### Qualidade de Código

| Categoria | Tecnologia | Uso |
|-----------|------------|-----|
| Linter | ruff | Lint e formatação |
| Type Checker | mypy | Verificação de tipos |
| Security Scanner | bandit | Análise de segurança |
| Pre-commit | pre-commit | Git hooks |

### GraphQL (Opcional)

| Categoria | Tecnologia | Uso |
|-----------|------------|-----|
| GraphQL | Strawberry | Schema e resolvers |


---

## Documentação

### Documentação Disponível

| Documento | Descrição | Localização |
|-----------|-----------|-------------|
| **Overview** | Visão geral do sistema | `docs/overview.md` |
| **Architecture** | Arquitetura detalhada | `docs/architecture.md` |
| **Modules** | Descrição dos módulos | `docs/modules.md` |
| **Patterns** | Padrões de implementação | `docs/patterns.md` |
| **Configuration** | Configuração completa | `docs/configuration.md` |
| **Getting Started** | Guia de início rápido | `docs/getting-started.md` |
| **Testing** | Guia de testes | `docs/testing.md` |
| **Deployment** | Guia de deploy | `docs/deployment.md` |

### Architecture Decision Records (ADRs)

| ADR | Título | Status |
|-----|--------|--------|
| ADR-001 | JWT Authentication | Accepted |
| ADR-002 | RBAC Implementation | Accepted |
| ADR-003 | API Versioning | Accepted |
| ADR-004 | Token Revocation | Accepted |
| ADR-005 | Repository Pattern | Accepted |
| ADR-006 | Specification Pattern | Accepted |
| ADR-007 | CQRS Implementation | Accepted |
| ADR-008 | Cache Strategy | Accepted |
| ADR-009 | Resilience Patterns | Accepted |
| ADR-010 | Error Handling | Accepted |
| ADR-011 | Observability Stack | Accepted |
| ADR-012 | Clean Architecture | Accepted |
| ADR-015 | Middleware Stack Order | Accepted |

### Guias

| Guia | Descrição |
|------|-----------|
| `docs/guides/getting-started.md` | Início rápido |
| `docs/guides/testing-guide.md` | Como escrever testes |
| `docs/guides/security-guide.md` | Práticas de segurança |
| `docs/guides/debugging-guide.md` | Debugging e troubleshooting |
| `docs/guides/integration-guide.md` | Integração com serviços |
| `docs/guides/cqrs-middleware-guide.md` | Usando CQRS |
| `docs/guides/bounded-context-guide.md` | Criando bounded contexts |

### API Documentation

| Documento | Descrição |
|-----------|-----------|
| `docs/api/openapi.yaml` | OpenAPI 3.1 spec |
| `docs/api/security.md` | Segurança da API |
| `docs/api/versioning.md` | Versionamento |
| `docs/api/rest/` | Endpoints REST |
| `docs/api/graphql/` | Schema GraphQL |

### Infrastructure

| Documento | Descrição |
|-----------|-----------|
| `docs/infrastructure/postgresql.md` | Configuração PostgreSQL |
| `docs/infrastructure/redis.md` | Configuração Redis |
| `docs/infrastructure/elasticsearch.md` | Configuração Elasticsearch |
| `docs/infrastructure/kafka.md` | Configuração Kafka |
| `docs/infrastructure/minio.md` | Configuração MinIO |

### Runbooks

| Runbook | Descrição |
|---------|-----------|
| `docs/runbooks/database-connection-issues.md` | Problemas de conexão DB |
| `docs/runbooks/cache-failures.md` | Falhas de cache |
| `docs/runbooks/circuit-breaker-open.md` | Circuit breaker aberto |


---

## Conformidade

| Padrão | Status | Descrição |
|--------|--------|-----------|
| **Clean Architecture** | ✅ 100% | Separação de camadas com dependências unidirecionais |
| **OWASP API Security Top 10** | ✅ 100% | Proteção contra vulnerabilidades comuns |
| **12-Factor App** | ✅ 100% | Cloud-native design |
| **RFC 7807** | ✅ Implementado | Problem Details for HTTP APIs |
| **RFC 8594** | ✅ Implementado | Deprecation Headers |
| **OpenAPI 3.1** | ✅ Implementado | Documentação automática |
| **SOLID Principles** | ✅ Implementado | Código manutenível |
| **DDD** | ✅ Implementado | Domain-Driven Design |

### Segurança Implementada

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
| Encryption | Field-level encryption para dados sensíveis |

---

## Criando uma Nova Entidade

### Método Manual

**1. Entidade** (`src/domain/products/entities.py`):
```python
from sqlmodel import SQLModel, Field
from ulid import ULID

class Product(SQLModel, table=True):
    __tablename__ = "products"
    
    id: str = Field(default_factory=lambda: str(ULID()), primary_key=True)
    name: str = Field(max_length=100)
    price: float = Field(ge=0)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)
```

**2. DTOs** (`src/application/products/dtos.py`):
```python
from pydantic import BaseModel, Field

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0)
    description: str | None = None

class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, ge=0)
    description: str | None = None

class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    description: str | None
    is_active: bool
    
    model_config = {"from_attributes": True}
```

**3. Router** (`src/interface/v1/products_router.py`):
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
) -> ProductResponse:
    product = Product(**data.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return ProductResponse.model_validate(product)

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProductResponse:
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return ProductResponse.model_validate(product)
```

**4. Migration**:
```bash
uv run alembic revision --autogenerate -m "Add products table"
uv run alembic upgrade head
```


---

## Troubleshooting

### Erro de Conexão com Database

```
sqlalchemy.exc.OperationalError: connection refused
```

**Solução:**
```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres

# Iniciar se necessário
docker compose -f deployments/docker/docker-compose.base.yml up -d postgres
```

### Erro de Secret Key

```
pydantic_core._pydantic_core.ValidationError: secret_key
```

**Solução:**
```bash
# Gerar chave segura
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Adicionar ao .env
SECURITY__SECRET_KEY=<chave_gerada>
```

### Erro de Importação

```
ModuleNotFoundError: No module named 'core'
```

**Solução:**
```bash
# Verificar PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

# Ou instalar em modo editável
pip install -e .
```

### Porta em Uso

```
OSError: [Errno 98] Address already in use
```

**Solução:**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>

# Ou usar outra porta
uvicorn src.main:app --port 8001
```

### Redis Connection Error

```
redis.exceptions.ConnectionError: Error connecting to localhost:6379
```

**Solução:**
```bash
# Iniciar Redis
docker compose -f deployments/docker/docker-compose.base.yml up -d redis

# Ou desabilitar Redis no .env
REDIS__ENABLED=false
```

---

## Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para diretrizes detalhadas.

### Resumo

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Faça suas alterações seguindo os coding standards
4. Escreva/atualize testes (cobertura mínima 80%)
5. Execute verificações (`make check`)
6. Commit (`git commit -m 'feat(scope): add nova feature'`)
7. Push (`git push origin feature/nova-feature`)
8. Abra um Pull Request

### Coding Standards

- **Arquivos:** kebab-case
- **Classes:** PascalCase
- **Funções/Variáveis:** snake_case
- **Constantes:** UPPER_SNAKE_CASE
- **Complexidade máxima:** 10
- **Linhas por arquivo:** 200-400 (máx 500)
- **Linhas por função:** 10-50 (máx 75)

---

## Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

---

## Links Úteis

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

---

<p align="center">
  Desenvolvido com ❤️ usando Python e FastAPI
</p>
