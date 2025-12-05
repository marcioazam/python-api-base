# ADR-015: CQRS Module Restructuring

**Status:** Accepted  
**Date:** 2025-12-05  
**Deciders:** Architecture Team

## Context

The `src/application/common/cqrs/` module contained multiple files with different responsibilities:
- `bus.py` - Main façade and re-exports
- `command_bus.py` - Command infrastructure
- `query_bus.py` - Query infrastructure
- `event_bus.py` - Event bus infrastructure
- `handlers.py` - Handler base classes
- `exceptions.py` - CQRS-specific exceptions

This flat structure made it difficult to navigate and understand the module's organization by responsibility.

## Decision

Reorganize the CQRS module into responsibility-separated subpackages:

```
cqrs/
├── commands/          # Command base class and CommandBus
│   ├── __init__.py
│   └── command_bus.py
├── queries/           # Query base class and QueryBus
│   ├── __init__.py
│   └── query_bus.py
├── events/            # EventBus and event handling
│   ├── __init__.py
│   └── event_bus.py
├── handlers/          # Handler base classes
│   ├── __init__.py
│   └── handlers.py
├── exceptions/        # CQRS-specific exceptions
│   ├── __init__.py
│   └── exceptions.py
├── bus.py             # Main façade and re-exports
└── __init__.py        # Public API
```

## Rationale

1. **Separation of Concerns**: Each subpackage groups related functionality
2. **Scalability**: Easier to add new features to specific areas
3. **Discoverability**: Clear structure helps developers find relevant code
4. **Maintainability**: Reduces cognitive load when working with specific patterns
5. **Backward Compatibility**: Public API remains unchanged via `bus.py` and `__init__.py`

## Consequences

### Positive
- Clear responsibility separation by CQRS pattern element
- Easier to locate and modify specific components
- Better organized for future extensions
- Improved code navigation and IDE support
- Maintains full backward compatibility

### Negative
- Slightly more files to manage
- Developers need to understand the new structure

### Neutral
- No performance impact
- No API changes for consumers

## Implementation Details

### File Movements
- `command_bus.py` → `commands/command_bus.py`
- `query_bus.py` → `queries/query_bus.py`
- `event_bus.py` → `events/event_bus.py`
- `handlers.py` → `handlers/handlers.py`
- `exceptions.py` → `exceptions/exceptions.py`
- `bus.py` → Remains as main façade

### Import Updates
- All internal imports updated to reflect new paths
- Public API maintained through `bus.py` and `__init__.py`
- All external imports continue to work unchanged

### Code Improvements
1. **command_bus.py**: Implemented `add_transaction_middleware()` with inline middleware
2. **query_bus.py**: Added `Awaitable` import for type hints
3. **exceptions.py**: Completed `MiddlewareError` class implementation
4. **Type Aliases**: Improved documentation for `CommandHandler` and `MiddlewareFunc`

## Validation

All imports tested and verified:
```python
from application.common.cqrs import (
    Command, CommandBus, CommandHandler, MiddlewareFunc,
    Query, QueryBus, QueryHandler,
    EventHandler, TypedEventBus,
    HandlerNotFoundError
)
```

## Related ADRs

- ADR-014: API Best Practices 2025
- ADR-013: SQLModel Production Readiness

## References

- **Feature**: `python-api-base-2025-state-of-art`
- **Validates**: Requirements 2.1, 2.2, 2.3, 2.4
