# ADR-016: Application Common Module Restructuring

**Status:** Accepted  
**Date:** 2025-12-05  
**Deciders:** Architecture Team

## Context

The `src/application/common/` module contained four directories with flat structures that made it difficult to navigate and understand the organization by responsibility:

- **dto/** - Generic DTOs (1 file)
- **errors/** - Exception classes (1 file)
- **mappers/** - Mapper implementations and interfaces (6 files)
- **export/** - Export/import functionality (8 files)

This flat structure violated the principle of separation of concerns and made the codebase harder to maintain.

## Decision

Reorganize each directory into responsibility-separated subpackages:

### 1. **dto/** → Organized by DTO type

```text
dto/
├── responses/          # API response wrappers
│   ├── api_response.py
│   ├── paginated_response.py
│   ├── problem_detail.py
│   └── __init__.py
├── requests/           # API request models
│   ├── bulk_delete.py
│   └── __init__.py
└── __init__.py         # Façade
```

### 2. **errors/** → Organized by error category

```text
errors/
├── base/               # Base error classes
│   ├── application_error.py
│   ├── handler_not_found.py
│   └── __init__.py
├── validation/         # Validation errors
│   ├── validation_error.py
│   └── __init__.py
├── not_found/          # Not found errors
│   ├── not_found_error.py
│   └── __init__.py
├── conflict/           # Conflict errors
│   ├── conflict_error.py
│   └── __init__.py
├── auth/               # Auth errors
│   ├── unauthorized_error.py
│   ├── forbidden_error.py
│   └── __init__.py
└── __init__.py         # Façade
```

### 3. **mappers/** → Organized by responsibility

```text
mappers/
├── interfaces/         # Interfaces and protocols
│   ├── mapper_interface.py
│   ├── mapper_protocol.py
│   └── __init__.py
├── implementations/    # Concrete implementations
│   ├── auto_mapper.py
│   ├── generic_mapper.py
│   └── __init__.py
├── errors/             # Mapper exceptions
│   ├── mapper_error.py
│   └── __init__.py
└── __init__.py         # Façade
```

### 4. **export/** → Organized by responsibility

```text
export/
├── base/               # Base façade
│   ├── data_export.py
│   └── __init__.py
├── exporters/          # Export functionality
│   ├── data_exporter.py
│   └── __init__.py
├── importers/          # Import functionality
│   ├── data_importer.py
│   └── __init__.py
├── serializers/        # Serialization
│   ├── data_serializer.py
│   └── __init__.py
├── formats/            # Format definitions
│   ├── export_format.py
│   └── __init__.py
├── config/             # Configuration
│   ├── export_config.py
│   └── __init__.py
├── results/            # Operation results
│   ├── export_result.py
│   ├── import_result.py
│   └── __init__.py
└── __init__.py         # Façade
```

## Rationale

- **Separation of Concerns**: Each subpackage groups related functionality by responsibility
- **Scalability**: Easier to add new features to specific areas without cluttering the main directory
- **Discoverability**: Clear structure helps developers find relevant code quickly
- **Maintainability**: Reduces cognitive load when working with specific patterns
- **Backward Compatibility**: Public API remains unchanged via façade `__init__.py` files
- **One Class Per File**: Follows Python best practices for file organization

## Consequences

### Positive

- Clear responsibility separation within each module
- Easier to locate and modify specific components
- Better organized for future extensions
- Improved code navigation and IDE support
- Maintains full backward compatibility
- Follows Python best practices

### Negative

- More files to manage (increased file count)
- Developers need to understand the new structure
- Slightly deeper import paths for internal use

### Neutral

- No performance impact
- No API changes for consumers
- No breaking changes

## Implementation Details

### File Movements

- **dto/**: `dto.py` → split into `responses/` and `requests/` subpackages
- **errors/**: `exceptions.py` → split into 5 subpackages by error category
- **mappers/**: 6 files → organized into 3 subpackages by responsibility
- **export/**: 8 files → organized into 7 subpackages by responsibility

### Import Updates

- All internal imports updated to reflect new paths
- All `__init__.py` files created with proper re-exports
- Public API maintained through façade pattern
- All external imports continue to work unchanged

### Code Improvements

- **Improved Documentation**: Added comprehensive docstrings to all modules
- **Better Organization**: Each file now has a single, clear responsibility
- **Type Hints**: Maintained and improved type hints throughout
- **Error Handling**: Structured error classes with proper inheritance
- **Backward Compatibility**: Façade pattern ensures no breaking changes

## Validation

All imports tested and verified:

```python
from application.common.dto import (
    ApiResponse, PaginatedResponse, BulkDeleteRequest, 
    BulkDeleteResponse, ProblemDetail
)
from application.common.errors import (
    ApplicationError, ValidationError, NotFoundError, 
    ConflictError, UnauthorizedError, ForbiddenError, 
    HandlerNotFoundError
)
from application.common.mappers import (
    AutoMapper, GenericMapper, IMapper, Mapper, MapperError
)
from application.common.export import (
    DataExporter, DataImporter, ExportConfig, 
    ExportFormat, ExportResult, ImportResult
)
```

## Related ADRs

- ADR-015: CQRS Module Restructuring
- ADR-014: API Best Practices 2025
- ADR-013: SQLModel Production Readiness

## References

- **Feature**: `architecture-restructuring-2025`
- **Pattern**: Façade Pattern for backward compatibility
- **Best Practice**: One class per file organization
