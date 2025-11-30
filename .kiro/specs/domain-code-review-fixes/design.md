# Design Document

## Overview

This design addresses code quality issues in the domain layer identified during code review. The primary focus is on:
1. Replacing naive datetime with timezone-aware datetime (Python 3.12+ compliance)
2. Improving DDD structure with proper module exports
3. Adding repository interfaces and value objects foundations

## Architecture

```
src/my_api/domain/
├── __init__.py              # Root exports
├── entities/
│   ├── __init__.py          # Entity exports with __all__
│   ├── audit_log.py         # Fixed: timezone-aware datetime
│   ├── item.py              # Fixed: timezone-aware datetime
│   └── role.py              # Fixed: timezone-aware datetime
├── repositories/
│   ├── __init__.py          # Repository interface exports
│   └── base.py              # Generic repository protocol
└── value_objects/
    ├── __init__.py          # Value object exports
    ├── money.py             # Money value object with Decimal
    └── entity_id.py         # Typed entity ID
```

## Components and Interfaces

### 1. Timezone-Aware Datetime Pattern

All entity datetime fields will use this consistent pattern:

```python
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime

class Entity(SQLModel, table=True):
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
```

### 2. Repository Interface Protocol

```python
from typing import Protocol, TypeVar, Generic
from collections.abc import Sequence

T = TypeVar("T")
ID = TypeVar("ID")

class RepositoryProtocol(Protocol[T, ID]):
    """Base repository interface for domain entities."""
    
    async def get_by_id(self, id: ID) -> T | None: ...
    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[T]: ...
    async def create(self, entity: T) -> T: ...
    async def update(self, entity: T) -> T: ...
    async def delete(self, id: ID) -> bool: ...
```

### 3. Value Objects

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    """Immutable money value object with currency."""
    amount: Decimal
    currency: str = "USD"
    
    def __add__(self, other: "Money") -> "Money": ...
    def __sub__(self, other: "Money") -> "Money": ...
```

## Data Models

No changes to data model structure, only datetime field configurations.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Entity Timestamps Are Timezone-Aware

*For any* domain entity instance created with default timestamps, the datetime fields should have tzinfo set to UTC and serialize with timezone information.

**Validates: Requirements 1.1, 1.3**

### Property 2: Value Object Equality

*For any* two value objects with identical attributes, they should be equal regardless of instance identity.

**Validates: Requirements 4.3**

## Error Handling

No new error types required. Existing validation errors apply.

## Testing Strategy

### Property-Based Testing

**Library**: Hypothesis (Python)
**Configuration**: Minimum 100 iterations per property test

### Unit Tests

- Verify datetime fields have timezone info
- Verify SQLAlchemy columns have timezone=True
- Verify module exports via __all__
- Verify repository protocol methods
- Verify value object immutability and equality
