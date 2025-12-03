# Type Definitions

## Overview

The types module provides type aliases and definitions for type safety across the application.

## Location

```
src/core/types/
├── __init__.py
├── id_types.py        # ID type definitions
├── json_types.py      # JSON-related types
├── numeric_types.py   # Numeric types
├── repository_types.py # Repository types
├── result_types.py    # Result pattern types
├── security_types.py  # Security types
└── string_types.py    # String types
```

## ID Types

### ULID

```python
from typing import NewType

ULID = NewType("ULID", str)

def generate_ulid() -> ULID:
    """Generate a new ULID."""
    import ulid
    return ULID(str(ulid.new()))
```

### UUID

```python
from uuid import UUID, uuid4

def generate_uuid() -> UUID:
    """Generate a new UUID."""
    return uuid4()
```

### EntityId

```python
EntityId = TypeVar("EntityId", str, UUID, int)
```

## Result Types

### Result Pattern

```python
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")

class Result(Generic[T, E]):
    """Result type for operations that can fail."""
    
    def __init__(
        self,
        value: T | None = None,
        error: E | None = None,
    ):
        self._value = value
        self._error = error
    
    @property
    def is_ok(self) -> bool:
        return self._error is None
    
    @property
    def is_err(self) -> bool:
        return self._error is not None
    
    def unwrap(self) -> T:
        if self._error is not None:
            raise ValueError(f"Called unwrap on Err: {self._error}")
        return self._value  # type: ignore
    
    def unwrap_err(self) -> E:
        if self._error is None:
            raise ValueError("Called unwrap_err on Ok")
        return self._error

def Ok(value: T) -> Result[T, E]:
    """Create successful result."""
    return Result(value=value)

def Err(error: E) -> Result[T, E]:
    """Create error result."""
    return Result(error=error)
```

### Usage

```python
async def create_user(data: UserCreate) -> Result[User, str]:
    if not validate_email(data.email):
        return Err("Invalid email format")
    
    user = User(**data.model_dump())
    await repository.add(user)
    return Ok(user)

# Using the result
result = await create_user(data)
if result.is_ok:
    user = result.unwrap()
else:
    error = result.unwrap_err()
```

## JSON Types

```python
from typing import Any, TypeAlias

JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)

JsonDict: TypeAlias = dict[str, JsonValue]
JsonList: TypeAlias = list[JsonValue]
```

## Repository Types

### Pagination

```python
@dataclass
class PaginationParams:
    """Pagination parameters."""
    page: int = 1
    page_size: int = 20
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size

@dataclass
class PaginatedResult(Generic[T]):
    """Paginated result."""
    items: list[T]
    total: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        return self.page > 1
```

### Sort

```python
from enum import Enum

class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"

@dataclass
class SortParams:
    """Sort parameters."""
    field: str
    order: SortOrder = SortOrder.ASC
```

## Security Types

### Token Types

```python
@dataclass
class TokenPayload:
    """JWT token payload."""
    sub: str  # Subject (user ID)
    exp: datetime  # Expiration
    iat: datetime  # Issued at
    jti: str  # JWT ID
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)

@dataclass
class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes
```

### Permission Types

```python
@dataclass
class Permission:
    """Permission definition."""
    resource: str
    action: str
    
    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"

@dataclass
class Role:
    """Role with permissions."""
    name: str
    permissions: list[Permission]
    
    def has_permission(self, resource: str, action: str) -> bool:
        return any(
            p.resource == resource and p.action == action
            for p in self.permissions
        )
```

## String Types

```python
from typing import Annotated
from pydantic import StringConstraints

# Email type with validation
Email = Annotated[str, StringConstraints(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")]

# Non-empty string
NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]

# Slug (URL-safe string)
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
```

## Numeric Types

```python
from decimal import Decimal
from typing import Annotated
from pydantic import Field

# Positive integer
PositiveInt = Annotated[int, Field(gt=0)]

# Non-negative integer
NonNegativeInt = Annotated[int, Field(ge=0)]

# Money (2 decimal places)
Money = Annotated[Decimal, Field(decimal_places=2)]

# Percentage (0-100)
Percentage = Annotated[float, Field(ge=0, le=100)]
```

## Related Documentation

- [Protocols](protocols.md)
- [Base Classes](base-classes.md)
