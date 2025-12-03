# DTOs and Mappers

## Overview

DTOs (Data Transfer Objects) são objetos para transferência de dados entre camadas. Mappers convertem entre entidades de domínio e DTOs.

## DTOs with Pydantic

### Response DTOs

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class UserDTO(BaseModel):
    """User data transfer object."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

class UserListDTO(BaseModel):
    """Paginated user list."""
    
    items: list[UserDTO]
    total: int
    skip: int
    limit: int
    
    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total
```

### Request DTOs

```python
from pydantic import BaseModel, Field, EmailStr

class CreateUserDTO(BaseModel):
    """DTO for creating a user."""
    
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)

class UpdateUserDTO(BaseModel):
    """DTO for updating a user."""
    
    name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
```

### Nested DTOs

```python
class OrderItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

class OrderDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    customer_id: str
    items: list[OrderItemDTO]
    total: Decimal
    status: str
    created_at: datetime
```

## Mappers

### Basic Mapper

```python
class UserMapper:
    """Maps between User entity and UserDTO."""
    
    @staticmethod
    def to_dto(entity: User) -> UserDTO:
        return UserDTO(
            id=entity.id,
            email=entity.email,
            name=entity.name,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    
    @staticmethod
    def to_entity(dto: CreateUserDTO) -> User:
        return User(
            id=str(ULID()),
            email=dto.email,
            name=dto.name,
            password_hash="",  # Set by command
            is_active=True,
            created_at=datetime.utcnow(),
        )
    
    @staticmethod
    def to_dto_list(entities: list[User]) -> list[UserDTO]:
        return [UserMapper.to_dto(e) for e in entities]
```

### Generic Mapper Protocol

```python
from typing import Protocol, TypeVar

TEntity = TypeVar("TEntity")
TDto = TypeVar("TDto")
TCreateDto = TypeVar("TCreateDto")

class Mapper(Protocol[TEntity, TDto, TCreateDto]):
    """Generic mapper protocol."""
    
    def to_dto(self, entity: TEntity) -> TDto: ...
    def to_entity(self, dto: TCreateDto) -> TEntity: ...
    def to_dto_list(self, entities: list[TEntity]) -> list[TDto]: ...
```

### Mapper with Dependencies

```python
class OrderMapper:
    """Maps Order with nested items."""
    
    def __init__(self, item_mapper: OrderItemMapper):
        self._item_mapper = item_mapper
    
    def to_dto(self, entity: Order) -> OrderDTO:
        return OrderDTO(
            id=entity.id,
            customer_id=entity.customer_id,
            items=[self._item_mapper.to_dto(i) for i in entity.items],
            total=entity.total,
            status=entity.status.value,
            created_at=entity.created_at,
        )
```

## Automatic Mapping

### Using model_validate

```python
class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    name: str

# Automatic mapping from entity
user_entity = User(id="123", email="test@example.com", name="Test")
user_dto = UserDTO.model_validate(user_entity)
```

### Using Field Aliases

```python
class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    user_id: str = Field(alias="id")
    email_address: str = Field(alias="email")
    full_name: str = Field(alias="name")
```

## Validation in DTOs

```python
from pydantic import field_validator, model_validator

class CreateUserDTO(BaseModel):
    email: EmailStr
    name: str
    password: str
    password_confirm: str
    
    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
    
    @model_validator(mode="after")
    def passwords_match(self) -> "CreateUserDTO":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self
```

## Usage in Use Cases

```python
class GetUserQuery(Query[UserDTO | None]):
    user_id: str
    
    async def execute(self, repository: IUserRepository) -> UserDTO | None:
        user = await repository.get(self.user_id)
        if user is None:
            return None
        return UserMapper.to_dto(user)

class ListUsersQuery(Query[UserListDTO]):
    skip: int = 0
    limit: int = 20
    
    async def execute(self, repository: IUserRepository) -> UserListDTO:
        users = await repository.get_all(skip=self.skip, limit=self.limit)
        total = await repository.count()
        
        return UserListDTO(
            items=UserMapper.to_dto_list(users),
            total=total,
            skip=self.skip,
            limit=self.limit,
        )
```

## Best Practices

1. **DTOs are immutable** - Don't modify after creation
2. **Validate in DTOs** - Use Pydantic validators
3. **Keep mappers simple** - Single responsibility
4. **Use from_attributes** - For automatic mapping
5. **Separate request/response DTOs** - Different validation needs
