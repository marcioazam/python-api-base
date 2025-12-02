# ADR-006: Specification Pattern

## Status
Accepted

## Context

The system needs a way to:
- Encapsulate business rules in reusable components
- Compose complex queries from simple predicates
- Translate business rules to database queries
- Keep domain logic independent of persistence

## Decision

We implement the Specification pattern with composable operators:

### Base Specification

```python
# src/domain/common/specification.py
class Specification[T](ABC):
    """Base specification for business rules."""

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies the specification."""
        ...

    def and_spec(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with AND logic."""
        return AndSpecification(self, other)

    def or_spec(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with OR logic."""
        return OrSpecification(self, other)

    def not_spec(self) -> "Specification[T]":
        """Negate the specification."""
        return NotSpecification(self)
```

### Comparison Operators

```python
class ComparisonOperator(Enum):
    EQ = "eq"           # Equal
    NE = "ne"           # Not equal
    GT = "gt"           # Greater than
    GE = "ge"           # Greater than or equal
    LT = "lt"           # Less than
    LE = "le"           # Less than or equal
    CONTAINS = "contains"       # String contains
    STARTS_WITH = "starts_with" # String starts with
    ENDS_WITH = "ends_with"     # String ends with
    IN = "in"           # Value in list
    IS_NULL = "is_null"         # Is null
    IS_NOT_NULL = "is_not_null" # Is not null
```

### Factory Functions

```python
# Convenience functions for creating specifications
equals[T, V](attribute: str, value: V) -> AttributeSpecification[T, V]
not_equals[T, V](attribute: str, value: V) -> AttributeSpecification[T, V]
greater_than[T, V](attribute: str, value: V) -> AttributeSpecification[T, V]
less_than[T, V](attribute: str, value: V) -> AttributeSpecification[T, V]
contains[T](attribute: str, value: str) -> AttributeSpecification[T, str]
is_null[T](attribute: str) -> AttributeSpecification[T, None]
is_not_null[T](attribute: str) -> AttributeSpecification[T, None]
```

### SQLAlchemy Integration

```python
# src/infrastructure/db/query_builder/
class SpecificationToSQLAlchemy[T]:
    """Convert specifications to SQLAlchemy filters."""

    def to_filter(
        self,
        spec: Specification[T],
        model: type[T],
    ) -> ColumnElement[bool]:
        """Convert specification to SQLAlchemy filter."""
        ...
```

### Usage Example

```python
# Define specifications
active_users = equals("is_active", True)
premium_users = equals("subscription", "premium")
recent_users = greater_than("created_at", last_month)

# Compose specifications
target_users = active_users.and_spec(premium_users).and_spec(recent_users)

# Use in repository
users = await user_repo.find_by_spec(target_users)
```

## Consequences

### Positive
- Reusable business rules
- Composable query logic
- Domain-independent of persistence
- Self-documenting code

### Negative
- Learning curve for team
- Some complex queries may not fit pattern
- Additional abstraction layer

### Neutral
- Requires SQLAlchemy adapter for database queries
- In-memory evaluation for testing

## Alternatives Considered

1. **Query objects** - Rejected as less composable
2. **Direct ORM queries** - Rejected as couples domain to persistence
3. **Expression trees** - Rejected as too complex for current needs

## References

- [src/domain/common/specification.py](../../src/domain/common/specification.py)
- [src/infrastructure/db/query_builder/](../../src/infrastructure/db/query_builder/)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
