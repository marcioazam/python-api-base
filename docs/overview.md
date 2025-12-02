# Python API Base - Visão Geral do Sistema

## Sumário Executivo

O **Python API Base** é um framework REST API enterprise-grade construído com FastAPI, seguindo princípios de Clean Architecture e Domain-Driven Design (DDD). O sistema foi projetado para maximizar reusabilidade através de Python Generics (PEP 695) e fornecer uma base sólida para aplicações de produção.

## Características Principais

| Categoria | Tecnologia | Versão |
|-----------|------------|--------|
| Framework Web | FastAPI | 0.115+ |
| Linguagem | Python | 3.12+ |
| ORM | SQLAlchemy + SQLModel | 2.0+ |
| Validação | Pydantic | 2.9+ |
| Observabilidade | OpenTelemetry + structlog | 1.28+ |
| Testes | pytest + Hypothesis | 8.3+ / 6.115+ |

## Arquitetura em Camadas

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

## Princípios de Design

1. **Clean Architecture** - Separação clara de responsabilidades
2. **Domain-Driven Design** - Modelagem rica do domínio
3. **SOLID Principles** - Código manutenível e extensível
4. **Type Safety** - Generics PEP 695 para máxima segurança de tipos
5. **Security First** - OWASP Top 10 compliance
6. **Observability** - Traces, Metrics, Logs integrados

## Estrutura de Diretórios

```
src/
├── core/           # Kernel da aplicação
│   ├── base/       # Classes base abstratas
│   ├── config/     # Configurações (Settings, Security, Observability)
│   ├── di/         # Container de Injeção de Dependência
│   ├── errors/     # Exception handlers RFC 7807
│   ├── protocols/  # Interfaces/Protocolos
│   ├── shared/     # Utilitários compartilhados
│   └── types/      # Type aliases e definições
│
├── domain/         # Camada de Domínio (DDD)
│   ├── common/     # Specification pattern, Value Objects base
│   ├── users/      # Bounded Context: Usuários
│   ├── items/      # Bounded Context: Items
│   └── examples/   # Bounded Context: Exemplos
│
├── application/    # Camada de Aplicação
│   ├── common/     # CQRS, Middleware, Batch operations
│   ├── services/   # Cross-cutting services
│   ├── users/      # Use cases de usuários
│   └── items/      # Use cases de items
│
├── infrastructure/ # Camada de Infraestrutura
│   ├── audit/      # Audit trail
│   ├── auth/       # Autenticação (JWT, Password)
│   ├── cache/      # Cache (Redis, Memory)
│   ├── db/         # Database (SQLAlchemy, Query Builder)
│   ├── elasticsearch/  # Search engine
│   ├── kafka/      # Event streaming
│   ├── minio/      # Object storage
│   ├── observability/  # Telemetry, Logging
│   ├── rbac/       # Role-Based Access Control
│   ├── redis/      # Redis client
│   ├── resilience/ # Circuit Breaker, Retry, Bulkhead
│   ├── storage/    # File storage abstraction
│   └── tasks/      # Background tasks (RabbitMQ)
│
├── interface/      # Camada de Interface
│   ├── errors/     # Error handlers
│   ├── graphql/    # GraphQL schema
│   ├── middleware/ # HTTP middleware
│   ├── routes/     # Route definitions
│   ├── v1/         # API v1 endpoints
│   ├── v2/         # API v2 endpoints
│   ├── versioning/ # API versioning
│   └── websocket/  # WebSocket handlers
│
└── main.py         # Application entry point
```

## Conformidade e Padrões

| Padrão | Status | Descrição |
|--------|--------|-----------|
| Clean Architecture | ✅ | Separação de camadas |
| OWASP API Security Top 10 | ✅ | Segurança de APIs |
| 12-Factor App | ✅ | Cloud-native design |
| RFC 7807 | ✅ | Problem Details for HTTP APIs |
| RFC 8594 | ✅ | Deprecation Headers |
| OpenAPI 3.1 | ✅ | API Documentation |

## Próximos Passos

- [Arquitetura Detalhada](architecture.md)
- [Componentes](components.md)
- [Módulos](modules.md)
- [Bibliotecas](libraries.md)
- [PRD](prd.md)
