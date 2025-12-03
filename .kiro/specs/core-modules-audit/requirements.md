# Requirements Document

## Introduction

Análise das pastas `src/core/protocols`, `src/core/shared` e `src/core/types` revelou problemas de código órfão, imports quebrados e módulos inexistentes referenciados em testes. O problema mais crítico é o router de examples (`src/interface/v1/examples/router.py`) que importa módulos inexistentes, impedindo a API de iniciar. Além disso, existem arquivos `.pyc` de módulos deletados e testes que importam módulos planejados mas nunca implementados.

## Glossary

- **Código Órfão**: Código que existe mas não é referenciado ou executado por nenhum fluxo do sistema
- **Import Quebrado**: Declaração de import que referencia módulo inexistente, causando ModuleNotFoundError
- **Módulo Stub**: Módulo mínimo criado para satisfazer imports sem implementação real
- **Router**: Componente FastAPI que define endpoints da API
- **ItemExample/PedidoExample**: Entidades de exemplo do sistema para demonstração de funcionalidades

## Requirements

### Requirement 1

**User Story:** As a developer, I want the examples router to import from correct module paths, so that the API can start successfully.

#### Acceptance Criteria

1. WHEN the API starts THEN the System SHALL load the examples router without ModuleNotFoundError
2. WHEN `interface.v1.examples.router` imports DTOs THEN the System SHALL use `application.examples` instead of `application.examples.dtos`
3. WHEN `interface.v1.examples.router` imports use cases THEN the System SHALL use `application.examples` instead of `application.examples.use_cases`

### Requirement 2

**User Story:** As a developer, I want to verify that core modules are connected to the application workflow, so that I can ensure no dead code exists.

#### Acceptance Criteria

1. WHEN analyzing `core.protocols` THEN the System SHALL verify each protocol is used by at least one implementation
2. WHEN analyzing `core.types` THEN the System SHALL verify each type is used in at least one DTO or entity
3. WHEN analyzing `core.shared` THEN the System SHALL verify each utility is imported by application code

### Requirement 3

**User Story:** As a developer, I want to clean up orphaned cache files, so that the project structure reflects actual code.

#### Acceptance Criteria

1. WHEN `.pyc` files exist for deleted modules THEN the System SHALL remove the orphaned cache files
2. WHEN cleaning cache THEN the System SHALL preserve cache files for existing modules
3. WHEN cleanup is complete THEN the System SHALL report the number of files removed

### Requirement 4

**User Story:** As a developer, I want to test the API manually via Docker, so that I can verify the examples endpoints work.

#### Acceptance Criteria

1. WHEN running `docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up` THEN the System SHALL start the API successfully
2. WHEN the API is running THEN the System SHALL expose ItemExample endpoints at `/api/v1/examples/items`
3. WHEN the API is running THEN the System SHALL expose PedidoExample endpoints at `/api/v1/examples/pedidos`

### Requirement 5

**User Story:** As a developer, I want integration tests for ItemExample and PedidoExample to pass, so that I can verify the core modules are properly connected.

#### Acceptance Criteria

1. WHEN running `pytest tests/integration/examples/` THEN the System SHALL execute all tests without import errors
2. WHEN tests import from `core.protocols` THEN the System SHALL resolve imports successfully
3. WHEN tests import from `core.types` THEN the System SHALL resolve imports successfully
4. WHEN tests import from `core.shared` THEN the System SHALL resolve imports successfully

## Appendix: Identified Issues

### Critical Bug - Router Imports

**File**: `src/interface/v1/examples/router.py`

**Broken Imports**:
```python
from application.examples.dtos import (...)      # DOES NOT EXIST
from application.examples.use_cases import (...) # DOES NOT EXIST
```

**Correct Imports**:
```python
from application.examples import (...)  # Re-exports from __init__.py
```

### Orphaned .pyc Files

Location: `src/core/shared/__pycache__/`

Files to remove:
- `code_review.cpython-313.pyc`
- `coverage_enforcement.cpython-313.pyc`
- `data_factory.cpython-313.pyc`
- `mock_server.cpython-313.pyc`
- `perf_baseline.cpython-313.pyc`
- `result.cpython-313.pyc`
- `runbook.cpython-313.pyc`
- `sdk_generator.cpython-313.pyc`
- `snapshot_testing.cpython-313.pyc`

### Core Modules Usage Summary

| Module | Status | Used By |
|--------|--------|---------|
| `core.protocols.AsyncRepository` | ✅ Active | Repositories, Use Cases |
| `core.protocols.CacheProvider` | ✅ Active | Cache implementations |
| `core.protocols.UnitOfWork` | ✅ Active | Use case base class |
| `core.types.ULID` | ✅ Active | Entity IDs |
| `core.types.Email` | ✅ Active | User DTOs |
| `core.shared.logging` | ✅ Active | main.py, all services |
| `core.shared.caching` | ✅ Active | Decorators, providers |
| `core.shared.utils.ids` | ✅ Active | ID generation |
| `core.shared.utils.password` | ✅ Active | Auth service |
