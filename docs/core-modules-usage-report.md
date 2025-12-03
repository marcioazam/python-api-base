# Core Modules Usage Report

**Feature: core-modules-audit**
**Generated: 2025-12-03**

## Overview

Este relatório documenta as conexões entre os módulos core (`core.protocols`, `core.types`, `core.shared`) e os exemplos do sistema (`ItemExample`, `PedidoExample`).

## Module Status Summary

| Module | Status | Used By |
|--------|--------|---------|
| `core.protocols` | ✅ Active | Repositories, Use Cases, Mappers |
| `core.types` | ✅ Active | DTOs, Entities, Validators |
| `core.shared.logging` | ✅ Active | main.py, All Services |
| `core.shared.caching` | ✅ Active | Decorators, Cache Providers |
| `core.shared.utils.ids` | ✅ Active | Entity ID Generation |
| `core.shared.utils.password` | ✅ Active | Auth Service |
| `core.shared.utils.time` | ✅ Active | Timestamps, Datetime Utils |

## Detailed Connections

### core.protocols

| Protocol | Used By | Purpose |
|----------|---------|---------|
| `AsyncRepository` | `ItemExampleRepository`, `PedidoExampleRepository` | Data access contract |
| `CacheProvider` | `InMemoryCacheProvider`, `RedisCacheProvider` | Cache abstraction |
| `UnitOfWork` | `BaseUseCase` | Transaction management |
| `Mapper` | `ItemExampleMapper`, `PedidoExampleMapper` | DTO conversion |
| `CommandHandler` | CQRS handlers | Command processing |
| `QueryHandler` | CQRS handlers | Query processing |

### core.types

| Type | Used By | Purpose |
|------|---------|---------|
| `ULID` | Entity IDs | Sortable unique identifiers |
| `UUID` | External IDs | Standard UUID format |
| `Email` | User DTOs | Email validation |
| `Password` | Auth DTOs | Password constraints |
| `PositiveInt` | Pagination | Positive integer validation |
| `PageSize` | Pagination | Page size limits (1-100) |
| `NonEmptyStr` | DTOs | Non-empty string validation |

### core.shared.logging

| Component | Used By | Purpose |
|-----------|---------|---------|
| `configure_logging` | `main.py` | Application startup |
| `get_logger` | All services | Structured logging |
| `RedactionProcessor` | Log pipeline | PII redaction |
| `set_correlation_id` | Middleware | Request tracing |

### core.shared.caching

| Component | Used By | Purpose |
|-----------|---------|---------|
| `cached` | Use cases | Method caching decorator |
| `generate_cache_key` | Cache utils | Key generation |
| `CacheConfig` | Configuration | Cache settings |
| `InMemoryCacheProvider` | Tests, Dev | In-memory cache |
| `RedisCacheProvider` | Production | Redis cache |

### core.shared.utils

| Utility | Used By | Purpose |
|---------|---------|---------|
| `generate_ulid` | Entity creation | ID generation |
| `generate_uuid7` | External IDs | Time-ordered UUIDs |
| `hash_password` | Auth service | Password hashing |
| `verify_password` | Auth service | Password verification |
| `utc_now` | Entities | Timestamp generation |
| `to_iso8601` | Serialization | Date formatting |

## ItemExample Connections

```
ItemExample
├── core.protocols
│   ├── AsyncRepository (ItemExampleRepository)
│   └── Mapper (ItemExampleMapper)
├── core.types
│   ├── ULID (entity ID)
│   ├── PositiveInt (quantity)
│   └── NonEmptyStr (name, sku)
└── core.shared
    ├── logging (get_logger)
    ├── caching (cached decorator)
    └── utils.ids (generate_ulid)
```

## PedidoExample Connections

```
PedidoExample
├── core.protocols
│   ├── AsyncRepository (PedidoExampleRepository)
│   └── Mapper (PedidoExampleMapper)
├── core.types
│   ├── ULID (entity ID)
│   ├── Email (customer_email)
│   └── PositiveInt (item quantities)
└── core.shared
    ├── logging (get_logger)
    ├── caching (cached decorator)
    └── utils.ids (generate_ulid)
```

## Unused/Orphaned Modules

The following modules were identified as orphaned (no source file, only .pyc cache):

| File | Status | Action Taken |
|------|--------|--------------|
| `core/shared/__pycache__/code_review.cpython-313.pyc` | Orphaned | Deleted |
| `core/shared/__pycache__/coverage_enforcement.cpython-313.pyc` | Orphaned | Deleted |
| `core/shared/__pycache__/data_factory.cpython-313.pyc` | Orphaned | Deleted |
| `core/shared/__pycache__/mock_server.cpython-313.pyc` | Orphaned | Deleted |
| `core/shared/__pycache__/perf_baseline.cpython-313.pyc` | Orphaned | Deleted |
| `core/shared/__pycache__/result.cpython-313.pyc` | Orphaned | Deleted |
| `core/shared/__pycache__/runbook.cpython-313.pyc` | Orphaned | Deleted |
| `core/shared/__pycache__/sdk_generator.cpython-313.pyc` | Orphaned | Deleted |
| `core/shared/__pycache__/snapshot_testing.cpython-313.pyc` | Orphaned | Deleted |

## Fixes Applied

### Router Import Fix

**File**: `src/interface/v1/examples/router.py`

**Before** (broken):
```python
from application.examples.dtos import (...)
from application.examples.use_cases import (...)
```

**After** (fixed):
```python
from application.examples import (
    # DTOs
    ItemExampleCreate,
    ItemExampleUpdate,
    ItemExampleResponse,
    ...
    # Use Cases
    ItemExampleUseCase,
    PedidoExampleUseCase,
    ...
)
```

## Test Results

| Test Suite | Tests | Status |
|------------|-------|--------|
| Integration (ItemExample) | 9 | ✅ Passed |
| Integration (PedidoExample) | 11 | ✅ Passed |
| Property (Core Modules) | 26 | ✅ Passed |
| **Total** | **46** | ✅ **All Passed** |


## Infrastructure Modules Audit (2025-12-03)

### Module Status Summary

| Module | Status | Workflow | Examples | Docker | Issues |
|--------|--------|----------|----------|--------|--------|
| `infrastructure.errors` | ✅ Active | ✅ | ✅ Indirect | ✅ | None |
| `infrastructure.httpclient` | ✅ Fixed | ⚠️ | ❌ | ⚠️ | Import bug fixed |
| `infrastructure.feature_flags` | ✅ Active | ✅ | ⚠️ Indirect | ✅ | None |
| `infrastructure.generics` | ⚠️ Partial | ⚠️ | ❌ | ⚠️ | Underutilized |
| `infrastructure.elasticsearch` | ⚠️ Partial | ❌ | ❌ | ❌ | Not in Docker |

### Detailed Analysis

#### infrastructure.errors

**Status**: ✅ Active in Workflow

**Imported by**:
- `infrastructure.db.session` - Uses `DatabaseError`
- `infrastructure.scylladb.client` - Uses `DatabaseError`
- `infrastructure.messaging.inbox` - Uses `MessagingError`
- `tests/unit/infrastructure/test_exceptions.py` - Unit tests
- `tests/properties/test_infrastructure_examples_integration_properties.py` - Property tests

**Connection to ItemExample/PedidoExample**: Indirectly via `infrastructure.db.session`

#### infrastructure.httpclient

**Status**: ✅ Fixed (was broken)

**Bug Found and Fixed**:
- Test file `test_client.py` was SKIPPED due to incorrect import
- **Cause**: Imported `RetryPolicy` from `infrastructure.httpclient.client` instead of `infrastructure.httpclient`
- **Fix Applied**: Changed import to use the package `__init__.py`

**Test Results**: 17 tests now passing

#### infrastructure.feature_flags

**Status**: ✅ Active in Workflow

**Imported by**:
- `infrastructure/__init__.py` - Exported in main module
- `interface/middleware/production.py` - Used in production middleware

**Connection to ItemExample/PedidoExample**: Indirectly via middleware (all requests pass through)

#### infrastructure.generics

**Status**: ⚠️ Partially Active

**Imported by**:
- `tests/properties/test_infrastructure_generics_properties.py` - Property tests only

**Issues**:
- Protocols defined (`Repository`, `Service`, `Factory`, `Store`) are not implemented by example repositories
- Potentially underutilized code

#### infrastructure.elasticsearch

**Status**: ⚠️ Partially Active

**Imported by**:
- `tests/unit/infrastructure/elasticsearch/test_document.py` - Unit tests
- `tests/unit/infrastructure/elasticsearch/test_repository.py` - Unit tests
- Internal elasticsearch modules

**Issues**:
- Not integrated into main workflow
- Elasticsearch not configured in docker-compose.base.yml or docker-compose.dev.yml
- Potentially orphaned code

### Fixes Applied

#### httpclient Test Import Fix

**File**: `tests/unit/infrastructure/httpclient/test_client.py`

**Before** (broken):
```python
pytest.skip("RetryPolicy not implemented in httpclient.client", allow_module_level=True)
from infrastructure.httpclient.client import (
    HttpClient,
    HttpClientConfig,
    HttpError,
    TimeoutError,
    ValidationError,
    RetryPolicy,  # NOT EXPORTED FROM client.py
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
```

**After** (fixed):
```python
from infrastructure.httpclient import (
    HttpClient,
    HttpClientConfig,
    HttpError,
    TimeoutError,
    ValidationError,
    RetryPolicy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
```

### Property Tests Added

**File**: `tests/properties/test_infrastructure_modules_audit_properties.py`

| Test Class | Tests | Status |
|------------|-------|--------|
| `TestInfrastructureModulesImport` | 5 | ✅ Passed |
| `TestActiveModulesReachability` | 3 | ✅ Passed |
| `TestErrorHierarchyConsistency` | 3 | ✅ Passed |
| **Total** | **11** | ✅ **All Passed** |

### Recommendations

1. **elasticsearch**: Add to docker-compose or document as future code
2. **generics**: Consider using protocols in example repositories
3. **httpclient**: Consider adding example endpoint that uses HTTP client
