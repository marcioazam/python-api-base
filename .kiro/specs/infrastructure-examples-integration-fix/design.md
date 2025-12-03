# Design Document: Infrastructure Examples Integration Fix

## Overview

This design addresses critical integration issues in the Examples system infrastructure. The primary goals are:

1. Add missing `get_async_session` function to the database session module
2. Configure the examples router to use real database repositories instead of mocks
3. Integrate examples bootstrap into application startup
4. Ensure end-to-end data persistence works correctly

## Architecture

The fix follows the existing layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  examples/router.py (FastAPI endpoints)              │   │
│  │  - Uses Depends() for DI                             │   │
│  │  - Injects real repositories via get_*_use_case()    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ItemExampleUseCase / PedidoExampleUseCase          │   │
│  │  - Business logic orchestration                      │   │
│  │  - Uses repository interfaces                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                       │
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │  db/session.py   │  │  db/repositories/examples.py   │  │
│  │  - get_async_    │  │  - ItemExampleRepository       │  │
│  │    session()     │  │  - PedidoExampleRepository     │  │
│  └──────────────────┘  └────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  di/examples_bootstrap.py                            │  │
│  │  - bootstrap_examples() called from main.py          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Database Session Module Enhancement

**File**: `src/infrastructure/db/session.py`

Add new async generator function:

```python
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session for FastAPI dependency injection.
    
    Yields:
        AsyncSession: Database session with automatic transaction management.
        
    Raises:
        DatabaseError: If database not initialized.
    """
    db = get_database_session()
    async with db.session() as session:
        yield session
```

### 2. Router Dependency Injection Fix

**File**: `src/interface/v1/examples/router.py`

Replace mock dependencies with real repository injection:

```python
async def get_item_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ItemExampleRepository:
    """Get ItemExampleRepository with injected session."""
    return ItemExampleRepository(session)

async def get_pedido_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PedidoExampleRepository:
    """Get PedidoExampleRepository with injected session."""
    return PedidoExampleRepository(session)

async def get_item_use_case(
    repo: ItemExampleRepository = Depends(get_item_repository),
) -> ItemExampleUseCase:
    """Get ItemExampleUseCase with real repository."""
    return ItemExampleUseCase(repository=repo)

async def get_pedido_use_case(
    item_repo: ItemExampleRepository = Depends(get_item_repository),
    pedido_repo: PedidoExampleRepository = Depends(get_pedido_repository),
) -> PedidoExampleUseCase:
    """Get PedidoExampleUseCase with real repositories."""
    return PedidoExampleUseCase(
        pedido_repo=pedido_repo,
        item_repo=item_repo,
    )
```

### 3. Application Startup Integration

**File**: `src/main.py`

Add examples bootstrap to lifespan:

```python
from infrastructure.di.examples_bootstrap import bootstrap_examples
from infrastructure.db.repositories.examples import (
    ItemExampleRepository,
    PedidoExampleRepository,
)

# In lifespan(), after CQRS bootstrap:
logger.info("Bootstrapping example handlers...")
db = get_database_session()
async with db.session() as session:
    item_repo = ItemExampleRepository(session)
    pedido_repo = PedidoExampleRepository(session)
    await bootstrap_examples(
        command_bus=command_bus,
        query_bus=query_bus,
        item_repository=item_repo,
        pedido_repository=pedido_repo,
    )
logger.info("Example handlers bootstrapped")
```

## Data Models

No changes to existing data models. The fix uses existing:

- `ItemExampleModel` - SQLAlchemy model for items
- `PedidoExampleModel` - SQLAlchemy model for orders
- `PedidoItemExampleModel` - SQLAlchemy model for order items

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, the following properties have been identified after consolidating redundant ones:

### Property 1: Async Session Yields Valid Session
*For any* call to `get_async_session()`, the yielded object SHALL be an instance of `AsyncSession` that is connected and usable for database operations.
**Validates: Requirements 1.1**

### Property 2: Session Transaction Round-Trip
*For any* entity written within a session context, reading that entity after the context commits SHALL return equivalent data.
**Validates: Requirements 1.2, 2.3**

### Property 3: Uninitialized Database Error
*For any* call to `get_async_session()` when the database is not initialized, the function SHALL raise a `DatabaseError`.
**Validates: Requirements 1.3**

### Property 4: Session Cleanup on Exit
*For any* session obtained via `get_async_session()`, after the context manager exits, the session SHALL be closed (not usable for new operations).
**Validates: Requirements 1.4**

### Property 5: Router Uses Real Repositories
*For any* request to the examples router, the injected use case SHALL contain real `ItemExampleRepository` or `PedidoExampleRepository` instances (not mocks).
**Validates: Requirements 2.1, 2.2**

### Property 6: Bootstrap Registers All Handlers
*For any* application startup with examples bootstrap, the CommandBus SHALL have handlers registered for all Item and Pedido commands, and QueryBus SHALL have handlers for all queries.
**Validates: Requirements 3.1, 3.2, 3.3**

### Property 7: Item Persistence Round-Trip
*For any* valid ItemExample created via the API, retrieving that item by ID SHALL return an item with equivalent essential fields (id, name, sku, price, quantity).
**Validates: Requirements 4.1, 4.2**

### Property 8: Pedido Persistence Round-Trip
*For any* valid PedidoExample created via the API, retrieving that pedido by ID SHALL return a pedido with equivalent essential fields and items.
**Validates: Requirements 4.3, 4.4**

## Error Handling

| Error Scenario | Handling Strategy |
|----------------|-------------------|
| Database not initialized | Raise `DatabaseError` with message "Database not initialized. Call init_database first." |
| Session commit failure | Rollback transaction, log error, re-raise exception |
| Repository not found | Return `None` from repository, use case returns `NotFoundError` |
| Validation failure | Return `ValidationError` from use case, router converts to HTTP 422 |
| Bootstrap failure | Log error, raise exception to prevent app startup |

## Testing Strategy

### Dual Testing Approach

This implementation uses both unit tests and property-based tests:

1. **Unit Tests**: Verify specific examples and edge cases
2. **Property-Based Tests**: Verify universal properties across all inputs

### Property-Based Testing Framework

**Framework**: `hypothesis` (Python)

**Configuration**:
- Minimum 100 iterations per property test
- Use `@settings(max_examples=100)` decorator

### Test Annotations

Each property-based test MUST include:
```python
# **Feature: infrastructure-examples-integration-fix, Property {N}: {property_text}**
# **Validates: Requirements X.Y**
```

### Test Categories

| Category | Tests |
|----------|-------|
| Unit Tests | Session creation, error handling, mock verification |
| Property Tests | Round-trip persistence, handler registration, session lifecycle |
| Integration Tests | Full API flow with database (existing tests) |

### Test Files

- `tests/unit/infrastructure/db/test_session.py` - Session unit tests
- `tests/properties/test_infrastructure_examples_integration_properties.py` - Property tests
