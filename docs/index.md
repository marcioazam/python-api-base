# Python API Base - Documentação

> **Última atualização:** Dezembro 2025 | **Versão:** 1.0.0

Bem-vindo à documentação completa do Python API Base Framework - um framework REST API enterprise-grade construído com FastAPI, seguindo Clean Architecture e Domain-Driven Design.

## Quick Start

| Ação | Link |
|------|------|
| 🚀 Começar | [Getting Started](guides/getting-started.md) |
| 🏗️ Arquitetura | [Architecture Overview](architecture.md) |
| 📚 API Reference | [API Documentation](api/index.md) |
| 🧪 Testes | [Testing Guide](testing/index.md) |

## Documentation Map

```
📁 docs/
├── 📖 Core Docs          → overview.md, architecture.md, getting-started.md
├── 🏛️ Layers             → layers/ (core, domain, application, infrastructure, interface)
├── 🔌 API                → api/ (REST, GraphQL, WebSocket)
├── 📋 ADRs               → adr/ (Architecture Decision Records)
├── 🛠️ Guides             → guides/ (contributing, integration, testing)
├── ⚙️ Operations         → operations/ (deployment, monitoring, runbooks)
├── 🧪 Testing            → testing/ (unit, integration, property, e2e)
├── 🔧 Infrastructure     → infrastructure/ (PostgreSQL, Redis, Kafka, MinIO)
└── 📝 Templates          → templates/ (ADR, runbook, module, test)
```

## By Role

### 👨‍💻 Developers
- [Getting Started](guides/getting-started.md) - Setup e primeiro endpoint
- [Layer Documentation](layers/index.md) - Entenda cada camada
- [Patterns](patterns.md) - Padrões de implementação
- [Testing Guide](testing/index.md) - Como testar
- [Contributing](guides/contributing.md) - Como contribuir

### 🏗️ Architects
- [Architecture](architecture.md) - Visão geral da arquitetura
- [ADRs](adr/README.md) - Decisões arquiteturais
- [Components](components.md) - Componentes do sistema
- [Modules](modules.md) - Módulos e dependências

### 🔧 DevOps/SRE
- [Deployment](operations/deployment.md) - Guia de deploy
- [Monitoring](operations/monitoring.md) - Observabilidade
- [Runbooks](operations/runbooks/README.md) - Procedimentos operacionais
- [Scaling](operations/scaling.md) - Escalabilidade

### 🔒 Security
- [Security Guide](guides/security-guide.md) - Práticas de segurança
- [API Security](api/security.md) - Segurança de API
- [RBAC](adr/ADR-002-rbac-implementation.md) - Controle de acesso

## Architecture Layers

| Layer | Responsabilidade | Documentação |
|-------|------------------|--------------|
| **Core** | Configuração, Protocolos, DI | [docs/layers/core/](layers/core/index.md) |
| **Domain** | Entidades, Value Objects, Specifications | [docs/layers/domain/](layers/domain/index.md) |
| **Application** | Use Cases, CQRS, DTOs | [docs/layers/application/](layers/application/index.md) |
| **Infrastructure** | Database, Cache, Messaging | [docs/layers/infrastructure/](layers/infrastructure/index.md) |
| **Interface** | REST API, GraphQL, WebSocket | [docs/layers/interface/](layers/interface/index.md) |

## Key Patterns

| Padrão | Descrição | Documentação |
|--------|-----------|--------------|
| Specification | Regras de negócio composáveis | [patterns.md#specification](patterns.md#1-specification-pattern) |
| CQRS | Separação leitura/escrita | [patterns.md#cqrs](patterns.md#2-cqrs-pattern) |
| Repository | Abstração de persistência | [patterns.md#repository](patterns.md#3-repository-pattern) |
| Resilience | Circuit Breaker, Retry, Bulkhead | [patterns.md#resilience](patterns.md#4-resilience-patterns) |

## ADRs (Architecture Decision Records)

| ADR | Título | Status |
|-----|--------|--------|
| [ADR-001](adr/ADR-001-jwt-authentication.md) | JWT Authentication | ✅ Accepted |
| [ADR-002](adr/ADR-002-rbac-implementation.md) | RBAC Implementation | ✅ Accepted |
| [ADR-003](adr/ADR-003-api-versioning.md) | API Versioning | ✅ Accepted |
| [ADR-005](adr/ADR-005-repository-pattern.md) | Repository Pattern | ✅ Accepted |
| [ADR-006](adr/ADR-006-specification-pattern.md) | Specification Pattern | ✅ Accepted |
| [ADR-007](adr/ADR-007-cqrs-implementation.md) | CQRS Implementation | ✅ Accepted |
| [ADR-012](adr/ADR-012-clean-architecture.md) | Clean Architecture | ✅ Accepted |

[Ver todos os ADRs →](adr/README.md)

## Tech Stack

| Categoria | Tecnologia | Versão |
|-----------|------------|--------|
| Framework | FastAPI | 0.115+ |
| Linguagem | Python | 3.12+ |
| ORM | SQLAlchemy + SQLModel | 2.0+ |
| Validação | Pydantic | 2.9+ |
| Database | PostgreSQL | 15+ |
| Cache | Redis | 7+ |
| Messaging | Kafka / RabbitMQ | - |
| Observability | OpenTelemetry + Prometheus | - |
| Testes | pytest + Hypothesis | 8.3+ / 6.115+ |

## Compliance

| Padrão | Status |
|--------|--------|
| Clean Architecture | ✅ |
| OWASP API Security Top 10 | ✅ |
| 12-Factor App | ✅ |
| RFC 7807 (Problem Details) | ✅ |
| RFC 8594 (Deprecation Headers) | ✅ |
| OpenAPI 3.1 | ✅ |

## Project Structure

```
python-api-base/
├── src/                    # Código fonte
│   ├── core/              # Kernel (config, DI, protocols)
│   ├── domain/            # Entidades e regras de negócio
│   ├── application/       # Use cases e DTOs
│   ├── infrastructure/    # Implementações (DB, cache, etc)
│   ├── interface/         # API (routers, middleware)
│   └── main.py            # Entry point
├── tests/                  # Testes (unit, integration, property, e2e)
├── docs/                   # Documentação
├── deployments/            # Docker, K8s, Terraform
├── scripts/                # Scripts utilitários
└── alembic/                # Database migrations
```

## Quick Links

- 📖 [Swagger UI](http://localhost:8000/docs)
- 📖 [ReDoc](http://localhost:8000/redoc)
- 📖 [OpenAPI Spec](http://localhost:8000/openapi.json)
- 🐙 [GitHub Repository](https://github.com/example/python-api-base)

## Contributing

Veja [CONTRIBUTING.md](../CONTRIBUTING.md) para diretrizes completas.

## License

MIT License - veja [LICENSE](../LICENSE) para detalhes.
