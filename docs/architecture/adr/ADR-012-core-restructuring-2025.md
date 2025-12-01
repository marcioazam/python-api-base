# ADR-012: Core Module Restructuring

## Status

Accepted

## Date

2025-12-01

## Context

A análise da estrutura `src/core/` identificou que alguns módulos continham implementações concretas misturadas com abstrações, violando o princípio de separação entre Core (abstrações) e Infrastructure (implementações).

### Problemas Identificados

1. **`core/auth/`** - Continha implementação JWT concreta
2. **`core/security/`** - Continha `audit_logger/` como implementação
3. **`core/container.py`** - Container de aplicação usando `dependency-injector` (implementação)

## Decision

Mover implementações concretas para `src/infrastructure/`:

| Origem | Destino |
|--------|---------|
| `core/auth/jwt/` | `infrastructure/auth/jwt/` |
| `core/auth/jwt_*.py` | `infrastructure/auth/` |
| `core/auth/password_policy.py` | `infrastructure/auth/` |
| `core/security/audit_logger/` | `infrastructure/security/audit_logger/` |
| `core/container.py` | `infrastructure/di/app_container.py` |

### Estrutura Final do Core

```text
src/core/
├── base/           # DDD building blocks (Entity, VO, AggregateRoot, Result)
├── config/         # Settings, logging config
├── di/             # Custom DI container (type-safe, PEP 695)
├── errors/         # Error hierarchy (domain, application, infrastructure)
├── patterns/       # Design patterns (Factory, Strategy, Observer, Pipeline)
├── protocols/      # Interfaces/Contracts (Protocol classes)
└── types/          # Shared type definitions
```

## Consequences

### Positivas

- **Separação clara**: Core contém apenas abstrações e protocolos
- **Clean Architecture**: Infrastructure layer contém todas as implementações
- **Testabilidade**: Facilita mocking de implementações
- **Substituibilidade**: Implementações podem ser trocadas sem afetar core

### Negativas

- **Breaking changes**: Imports antigos de `core.auth` precisam ser atualizados
- **Migration effort**: Projetos dependentes precisam atualizar imports

### Neutras

- Dois containers DI coexistem:
  - `core/di/` - Container customizado type-safe (PEP 695)
  - `infrastructure/di/` - Container com `dependency-injector` para wiring da aplicação

## Imports Atualizados

```python
# Antes
from my_app.core.auth.jwt import JWTService
from my_app.core.container import Container, lifecycle

# Depois
from my_app.infrastructure.auth import JWTService
from my_app.infrastructure.di import Container, lifecycle
```

## Alternatives Considered

1. **Manter estrutura atual**: Rejeitado - viola Clean Architecture
2. **Criar `core/interfaces/` separado**: Desnecessário - `protocols/` já serve esse propósito
3. **Unificar containers DI**: Adiado - ambos servem propósitos diferentes

## References

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)
