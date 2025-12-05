# ADR-016: Core Modules Restructuring into Subpastas (2025)

**Status:** Accepted  
**Date:** 2025-12-05  
**Author:** Architecture Team

## Context

Reorganized three core modules (`core/di`, `core/protocols`, `core/types`) into subpastas by responsibility and objective, as requested. This decision follows the pattern established in `core/config` restructuring.

## Decision

### Reorganization Structure

#### core/di → 4 Subpastas

```
core/di/
├── container/
│   ├── __init__.py (façade)
│   ├── container.py (Container class)
│   └── scopes.py (Scope class)
├── resolution/
│   ├── __init__.py (façade)
│   ├── resolver.py (Resolver class)
│   └── exceptions.py (4 DI exceptions)
├── lifecycle/
│   ├── __init__.py (façade)
│   └── lifecycle.py (Lifetime enum, Registration dataclass)
├── observability/
│   ├── __init__.py (façade)
│   └── metrics.py (MetricsTracker, ContainerStats, ContainerHooks)
└── __init__.py (main façade)
```

**Rationale:**
- `container/`: Orchestration and scope management
- `resolution/`: Dependency resolution logic and error handling
- `lifecycle/`: Service lifetime management
- `observability/`: Metrics and monitoring

#### core/protocols → 4 Subpastas

```
core/protocols/
├── entity/
│   ├── __init__.py (façade)
│   └── base.py (Identifiable, Timestamped, SoftDeletable)
├── application/
│   ├── __init__.py (façade)
│   └── application.py (EventHandler, Command, Query, Mapper)
├── data_access/
│   ├── __init__.py (façade)
│   ├── data_access.py (AsyncRepository, CacheProvider, UnitOfWork)
│   └── repository.py (AsyncRepository, CommandHandler, QueryHandler)
├── domain/
│   ├── __init__.py (façade)
│   └── entities.py (Entity, TrackedEntity, VersionedEntity, etc)
└── __init__.py (main façade)
```

**Rationale:**
- `entity/`: Base entity trait protocols
- `application/`: Application layer patterns (CQRS, events, mappers)
- `data_access/`: Data access patterns (repositories, caches)
- `domain/`: Domain entity protocols

#### core/types → 4 Subpastas

```
core/types/
├── identity/
│   ├── __init__.py (façade)
│   └── id_types.py (ULID, UUID, UUID7, EntityId)
├── data/
│   ├── __init__.py (façade)
│   ├── json_types.py (JSON types)
│   ├── numeric_types.py (Numeric types)
│   └── string_types.py (String types)
├── patterns/
│   ├── __init__.py (façade)
│   └── result_types.py (Result pattern, callbacks)
├── domain/
│   ├── __init__.py (façade)
│   ├── repository_types.py (Repository types)
│   └── security_types.py (Security types)
└── __init__.py (main façade)
```

**Rationale:**
- `identity/`: ID type definitions
- `data/`: Data type definitions (JSON, numeric, string)
- `patterns/`: Pattern-based types (Result, callbacks)
- `domain/`: Domain-specific types (repository, security)

### Improvements Applied

1. **Updated all imports** in moved files to reflect new structure
2. **Created façade `__init__.py`** files in each subpasta for clean API
3. **Maintained backward compatibility** - all exports available from main modules
4. **Validated compilation** - all modules compile without errors
5. **Tested imports** - all public APIs working correctly

## Consequences

### Positive
- ✅ Clear separation of concerns within each module
- ✅ Better code organization by responsibility
- ✅ Easier to locate and maintain related code
- ✅ Scalable structure for future additions
- ✅ Consistent with `core/config` restructuring pattern
- ✅ All imports validated and working

### Neutral
- No breaking changes to public APIs
- All exports remain accessible from main modules
- Backward compatibility maintained

## Validation

### Structure Validation
```
core/di/: 4 subpastas + 7 files ✅
core/protocols/: 4 subpastas + 6 files ✅
core/types/: 4 subpastas + 8 files ✅
```

### Import Validation
```
from core.di import Container, Lifetime, CircularDependencyError ✅
from core.protocols import AsyncRepository, Entity, Command, Query ✅
from core.types import Email, UUID, EntityId, URLPath, PercentageRange ✅
```

### Compilation
```
python -m compileall src/core/di src/core/protocols src/core/types ✅
```

## Files Modified

### core/di
- Moved: container.py → container/container.py
- Moved: scopes.py → container/scopes.py
- Moved: resolver.py → resolution/resolver.py
- Moved: exceptions.py → resolution/exceptions.py
- Moved: lifecycle.py → lifecycle/lifecycle.py
- Moved: metrics.py → observability/metrics.py
- Updated: container/container.py imports
- Updated: resolution/resolver.py imports
- Updated: container/scopes.py imports
- Updated: __init__.py (main façade)

### core/protocols
- Moved: base.py → entity/base.py
- Moved: application.py → application/application.py
- Moved: data_access.py → data_access/data_access.py
- Moved: repository.py → data_access/repository.py
- Moved: entities.py → domain/entities.py
- Updated: domain/entities.py imports
- Updated: __init__.py (main façade)

### core/types
- Moved: id_types.py → identity/id_types.py
- Moved: json_types.py → data/json_types.py
- Moved: numeric_types.py → data/numeric_types.py
- Moved: string_types.py → data/string_types.py
- Moved: result_types.py → patterns/result_types.py
- Moved: repository_types.py → domain/repository_types.py
- Moved: security_types.py → domain/security_types.py
- Updated: __init__.py (main façade)

## Related ADRs

- ADR-015: Core Modules Review and Improvements 2025
- ADR-014: API Best Practices 2025
- ADR-013: SQLModel Production Readiness

## Migration Guide

### For Existing Code

All imports remain the same:
```python
# These still work exactly as before
from core.di import Container, Lifetime
from core.protocols import AsyncRepository, Entity
from core.types import Email, UUID
```

No changes needed to existing code!

## References

- PEP 695: Type Parameter Syntax
- Python Package Structure Best Practices
- Domain-Driven Design principles
