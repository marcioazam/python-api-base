# REST API

## Overview

A API REST é implementada com FastAPI, seguindo padrões RESTful e OpenAPI 3.1.

## Router Structure

```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 20,
    query_bus: QueryBus = Depends(get_query_bus),
) -> list[UserResponse]:
    """List users with pagination."""
    result = await query_bus.dispatch(ListUsersQuery(skip=skip, limit=limit))
    return [UserResponse.from_dto(u) for u in result.items]

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    query_bus: QueryBus = Depends(get_query_bus),
) -> UserResponse:
    """Get user by ID."""
    result = await query_bus.dispatch(GetUserQuery(user_id=user_id))
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserResponse.from_dto(result)

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: CreateUserRequest,
    command_bus: CommandBus = Depends(get_command_bus),
) -> UserResponse:
    """Create a new user."""
    result = await command_bus.dispatch(CreateUserCommand(**data.model_dump()))
    if result.is_err():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, result.error)
    return UserResponse.from_dto(result.value)
```

## Request/Response Models

```python
from pydantic import BaseModel, Field, EmailStr

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8)

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime
    
    @classmethod
    def from_dto(cls, dto: UserDTO) -> "UserResponse":
        return cls(**dto.model_dump())
```

## Error Responses (RFC 7807)

```python
{
    "type": "https://api.example.com/errors/not-found",
    "title": "Not Found",
    "status": 404,
    "detail": "User with id 'abc123' not found",
    "instance": "/api/v1/users/abc123"
}
```

## Pagination

```python
class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    skip: int
    limit: int
    
    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total
```

## Filtering

```python
@router.get("/")
async def list_users(
    skip: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
    search: str | None = None,
) -> PaginatedResponse[UserResponse]:
    query = ListUsersQuery(
        skip=skip,
        limit=limit,
        is_active=is_active,
        search=search,
    )
    return await query_bus.dispatch(query)
```

## Best Practices

1. **Use HTTP status codes correctly** - 201 for create, 204 for delete
2. **Return consistent error format** - RFC 7807
3. **Use Pydantic for validation** - Automatic OpenAPI docs
4. **Paginate list endpoints** - Prevent large responses
5. **Use dependency injection** - For testability
