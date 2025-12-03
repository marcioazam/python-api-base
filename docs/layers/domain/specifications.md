# Specification Pattern

## Overview

O Specification Pattern encapsula regras de negócio em objetos composáveis, permitindo combinar condições usando operadores lógicos (AND, OR, NOT).

## Base Specification

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")

class Specification(ABC, Generic[T]):
    """Base specification class."""
    
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies specification."""
        ...
    
    def and_spec(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with AND."""
        return AndSpecification(self, other)
    
    def or_spec(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with OR."""
        return OrSpecification(self, other)
    
    def not_spec(self) -> "Specification[T]":
        """Negate specification."""
        return NotSpecification(self)
```

## Composite Specifications

```python
class AndSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return (
            self.left.is_satisfied_by(candidate) and
            self.right.is_satisfied_by(candidate)
        )

class OrSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return (
            self.left.is_satisfied_by(candidate) or
            self.right.is_satisfied_by(candidate)
        )

class NotSpecification(Specification[T]):
    def __init__(self, spec: Specification[T]):
        self.spec = spec
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return not self.spec.is_satisfied_by(candidate)
```

## Comparison Operators

```python
from enum import Enum

class ComparisonOperator(Enum):
    EQ = "eq"           # Equal
    NE = "ne"           # Not equal
    GT = "gt"           # Greater than
    GE = "ge"           # Greater or equal
    LT = "lt"           # Less than
    LE = "le"           # Less or equal
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
```

## Factory Functions

```python
def equals[T, V](attribute: str, value: V) -> Specification[T]:
    """Create equality specification."""
    return AttributeSpecification(attribute, ComparisonOperator.EQ, value)

def not_equals[T, V](attribute: str, value: V) -> Specification[T]:
    return AttributeSpecification(attribute, ComparisonOperator.NE, value)

def greater_than[T, V](attribute: str, value: V) -> Specification[T]:
    return AttributeSpecification(attribute, ComparisonOperator.GT, value)

def less_than[T, V](attribute: str, value: V) -> Specification[T]:
    return AttributeSpecification(attribute, ComparisonOperator.LT, value)

def contains[T](attribute: str, value: str) -> Specification[T]:
    return AttributeSpecification(attribute, ComparisonOperator.CONTAINS, value)

def is_null[T](attribute: str) -> Specification[T]:
    return AttributeSpecification(attribute, ComparisonOperator.IS_NULL, None)

def is_not_null[T](attribute: str) -> Specification[T]:
    return AttributeSpecification(attribute, ComparisonOperator.IS_NOT_NULL, None)
```

## Usage Examples

### Simple Specifications

```python
# Single condition
active_users = equals("is_active", True)
premium_users = equals("subscription", "premium")

# Check if user satisfies
user = User(is_active=True, subscription="premium")
assert active_users.is_satisfied_by(user)
```

### Composite Specifications

```python
# AND composition
active_premium = active_users.and_spec(premium_users)

# OR composition
special_users = active_users.or_spec(premium_users)

# NOT composition
inactive_users = active_users.not_spec()

# Complex composition
target_users = (
    equals("is_active", True)
    .and_spec(equals("subscription", "premium"))
    .and_spec(is_null("deleted_at"))
    .and_spec(greater_than("age", 18))
)
```

### Domain-Specific Specifications

```python
class ActiveUserSpecification(Specification[User]):
    def is_satisfied_by(self, user: User) -> bool:
        return user.is_active and user.deleted_at is None

class PremiumUserSpecification(Specification[User]):
    def __init__(self, min_days: int = 30):
        self.min_days = min_days
    
    def is_satisfied_by(self, user: User) -> bool:
        if user.subscription != "premium":
            return False
        days = (datetime.now() - user.subscription_start).days
        return days >= self.min_days

# Usage
active = ActiveUserSpecification()
premium = PremiumUserSpecification(min_days=60)
target = active.and_spec(premium)
```

## SQLAlchemy Conversion

```python
class SpecificationToSQLAlchemy:
    """Convert specification to SQLAlchemy filter."""
    
    def to_filter(self, spec: Specification, model: type) -> Any:
        if isinstance(spec, AndSpecification):
            return and_(
                self.to_filter(spec.left, model),
                self.to_filter(spec.right, model),
            )
        elif isinstance(spec, OrSpecification):
            return or_(
                self.to_filter(spec.left, model),
                self.to_filter(spec.right, model),
            )
        elif isinstance(spec, NotSpecification):
            return not_(self.to_filter(spec.spec, model))
        elif isinstance(spec, AttributeSpecification):
            column = getattr(model, spec.attribute)
            return self._apply_operator(column, spec.operator, spec.value)
    
    def _apply_operator(self, column, operator, value):
        match operator:
            case ComparisonOperator.EQ:
                return column == value
            case ComparisonOperator.NE:
                return column != value
            case ComparisonOperator.GT:
                return column > value
            case ComparisonOperator.CONTAINS:
                return column.contains(value)
            case ComparisonOperator.IS_NULL:
                return column.is_(None)
            # ... other operators
```

## Repository Usage

```python
class UserRepository:
    async def find_by_spec(self, spec: Specification[User]) -> list[User]:
        converter = SpecificationToSQLAlchemy()
        filter_clause = converter.to_filter(spec, UserModel)
        
        result = await self._session.execute(
            select(UserModel).where(filter_clause)
        )
        return result.scalars().all()

# Usage
spec = equals("is_active", True).and_spec(is_null("deleted_at"))
users = await repository.find_by_spec(spec)
```
