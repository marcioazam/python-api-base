# DTOs (Data Transfer Objects)

## Overview

DTOs define data contracts at application boundaries, separating internal domain models from external representations.

## DTO Types

### Request DTOs

```python
from pydantic import BaseModel, Field, EmailStr

class UserCreateDTO(BaseModel):
    """DTO for creating a user."""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)

class UserUpdateDTO(BaseModel):
    """DTO for updating a user."""
    name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
```

### Response DTOs

```python
class UserResponseDTO(BaseModel):
    """DTO for user response."""
    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime
    
    @classmethod
    def from_entity(cls, user: User) -> "UserResponseDTO":
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
```

### Paginated Response

```python
class PaginatedResponseDTO(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

## Validation

Pydantic provides automatic validation:

```python
class ItemCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    price: Decimal = Field(..., ge=0, decimal_places=2)
    quantity: int = Field(default=0, ge=0)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()
```

## Best Practices

1. **Separate request/response DTOs**
2. **Use Pydantic validation**
3. **Include factory methods** (`from_entity`)
4. **Keep DTOs flat** when possible
5. **Document all fields**

## Related

- [Mappers](mappers.md)
- [CQRS](cqrs.md)
