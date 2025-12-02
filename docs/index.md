# Python API Base - Documentação

## Índice de Documentação

Bem-vindo à documentação completa do Python API Base Framework.

---

## Documentos Disponíveis

### Visão Geral

| Documento | Descrição |
|-----------|-----------|
| [Overview](overview.md) | Visão geral do sistema e características principais |
| [PRD](prd.md) | Product Requirements Document - requisitos e roadmap |

### Arquitetura

| Documento | Descrição |
|-----------|-----------|
| [Architecture](architecture.md) | Arquitetura detalhada do sistema |
| [Layers](layers.md) | Descrição das camadas e regras de dependência |
| [Components](components.md) | Componentes do sistema e suas interfaces |
| [Modules](modules.md) | Módulos e suas responsabilidades |
| [Patterns](patterns.md) | Padrões de implementação (Specification, CQRS, Repository, Resilience) |

### Referência Técnica

| Documento | Descrição |
|-----------|-----------|
| [Libraries](libraries.md) | Bibliotecas e dependências utilizadas |
| [API Reference](api/README.md) | Documentação da API REST |
| [Security](api/security.md) | Práticas de segurança |
| [Versioning](api/versioning.md) | Estratégias de versionamento |

### Guias

| Documento | Descrição |
|-----------|-----------|
| [Getting Started](getting-started.md) | Guia de início rápido |
| [Configuration](configuration.md) | Configuração do sistema |
| [Deployment](deployment.md) | Guia de deploy |
| [Testing](testing.md) | Guia de testes (unit, property-based, integration) |
| [Bounded Context Guide](guides/bounded-context-guide.md) | Como criar um novo bounded context |
| [Integration Guide](guides/integration-guide.md) | Como adicionar novas integrações |

### Operações

| Documento | Descrição |
|-----------|-----------|
| [Monitoring](monitoring.md) | Métricas, traces e logs |
| [Runbooks](runbooks/README.md) | Procedimentos operacionais |

### ADRs (Architecture Decision Records)

| ADR | Título |
|-----|--------|
| [ADR-001](adr/ADR-001-jwt-authentication.md) | JWT Authentication Strategy |
| [ADR-002](adr/ADR-002-rbac-implementation.md) | RBAC Implementation |
| [ADR-003](adr/ADR-003-api-versioning.md) | API Versioning Strategy |
| [ADR-004](adr/ADR-004-token-revocation.md) | Token Revocation via Redis |
| [ADR-005](adr/ADR-005-repository-pattern.md) | Generic Repository Pattern |
| [ADR-006](adr/ADR-006-specification-pattern.md) | Specification Pattern |
| [ADR-007](adr/ADR-007-cqrs-implementation.md) | CQRS Implementation |
| [ADR-008](adr/ADR-008-cache-strategy.md) | Cache Strategy |
| [ADR-009](adr/ADR-009-resilience-patterns.md) | Resilience Patterns |
| [ADR-010](adr/ADR-010-error-handling.md) | Error Handling (RFC 7807) |
| [ADR-011](adr/ADR-011-observability-stack.md) | Observability Stack |
| [ADR-012](adr/ADR-012-clean-architecture.md) | Clean Architecture Layers |

### Runbooks

| Runbook | Descrição |
|---------|-----------|
| [Database Connection Issues](runbooks/database-connection-issues.md) | Problemas de conexão com banco |
| [Cache Failures](runbooks/cache-failures.md) | Falhas de cache Redis |
| [Circuit Breaker Open](runbooks/circuit-breaker-open.md) | Circuit breaker aberto |

---

## Estrutura do Projeto

```
python-api-base/
├── src/                    # Código fonte
│   ├── core/              # Kernel da aplicação
│   ├── domain/            # Camada de domínio
│   ├── application/       # Camada de aplicação
│   ├── infrastructure/    # Camada de infraestrutura
│   ├── interface/         # Camada de interface
│   └── main.py            # Entry point
├── tests/                  # Testes
│   ├── unit/              # Testes unitários
│   ├── integration/       # Testes de integração
│   ├── properties/        # Property-based tests
│   └── e2e/               # Testes end-to-end
├── docs/                   # Documentação
│   ├── adr/               # Architecture Decision Records
│   ├── api/               # Documentação de API
│   ├── guides/            # Guias de implementação
│   └── runbooks/          # Procedimentos operacionais
├── deployments/            # Configurações de deploy
│   ├── docker/            # Docker configs
│   ├── k8s/               # Kubernetes manifests
│   ├── helm/              # Helm charts
│   └── terraform/         # Infrastructure as Code
├── scripts/                # Scripts utilitários
└── alembic/                # Database migrations
```

---

## Quick Links

### Desenvolvimento

- [Instalação](getting-started.md#instalação)
- [Configuração](configuration.md)
- [Executando localmente](getting-started.md#executando)
- [Testes](testing.md)
- [Contributing](../CONTRIBUTING.md)

### API

- [Swagger UI](http://localhost:8000/docs)
- [ReDoc](http://localhost:8000/redoc)
- [OpenAPI Spec](http://localhost:8000/openapi.json)

### Operações

- [Health Checks](api/README.md#health-checks)
- [Métricas](monitoring.md#prometheus-metrics)
- [Logs](monitoring.md#structured-logs)
- [Runbooks](runbooks/README.md)

---

## Stack Tecnológica

| Categoria | Tecnologia |
|-----------|------------|
| Framework | FastAPI 0.115+ |
| Linguagem | Python 3.12+ |
| ORM | SQLAlchemy 2.0+ / SQLModel |
| Validação | Pydantic 2.9+ |
| Database | PostgreSQL 15+ |
| Cache | Redis 7+ |
| Messaging | Kafka / RabbitMQ |
| Search | Elasticsearch 8+ |
| Storage | MinIO / S3 |
| Observability | OpenTelemetry / Prometheus |
| Testes | pytest / Hypothesis |

---

## Conformidade

| Padrão | Status |
|--------|--------|
| Clean Architecture | ✅ |
| OWASP API Security Top 10 | ✅ |
| 12-Factor App | ✅ |
| RFC 7807 (Problem Details) | ✅ |
| RFC 8594 (Deprecation Headers) | ✅ |
| OpenAPI 3.1 | ✅ |

---

## Contribuindo

Veja [CONTRIBUTING.md](../CONTRIBUTING.md) para diretrizes completas.

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Add nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## Licença

MIT License - veja [LICENSE](../LICENSE) para detalhes.
