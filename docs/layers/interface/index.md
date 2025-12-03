# Interface Layer

## Overview

A **Interface Layer** expõe a API via HTTP (REST), GraphQL e WebSocket, incluindo middleware, validação e serialização.

## Directory Structure

```
src/interface/
├── __init__.py
├── dependencies.py          # FastAPI dependencies
├── openapi.py              # OpenAPI customization
├── router.py               # Main router
├── errors/                  # Error handlers
├── graphql/                 # GraphQL schema
├── middleware/              # HTTP middleware
├── v1/                      # API v1 endpoints
├── v2/                      # API v2 endpoints
├── versioning/              # Version strategies
└── websocket/               # WebSocket handlers
```

## Key Components

| Component | Documentation |
|-----------|---------------|
| REST API | [rest-api.md](rest-api.md) |
| GraphQL | [graphql.md](graphql.md) |
| WebSocket | [websocket.md](websocket.md) |
| Middleware | [middleware.md](middleware.md) |

## Dependency Rules

### Allowed Imports ✅
```python
# Application layer
from application.users.dtos import UserDTO, CreateUserDTO
from application.users.commands import CreateUserCommand

# Infrastructure (auth only)
from infrastructure.auth.jwt import JWTService

# Core
from core.config import get_settings
```

### Prohibited Imports ❌
```python
# Domain entities directly
from domain.users.entities import User  # ❌

# Infrastructure implementations
from infrastructure.db.session import get_session  # ❌
```

## Router Definition

```python
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    data: CreateUserRequest,
    command_bus: CommandBus = Depends(get_command_bus),
) -> UserResponse:
    command = CreateUserCommand(**data.model_dump())
    result = await command_bus.dispatch(command)
    
    if result.is_err():
        raise HTTPException(400, detail=result.error)
    
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
    created_at: datetime
    
    @classmethod
    def from_dto(cls, dto: UserDTO) -> "UserResponse":
        return cls(**dto.model_dump())
```

## Dependencies

```python
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(
    token: str = Depends(security),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> UserDTO:
    try:
        payload = jwt_service.verify(token.credentials)
        return await get_user_by_id(payload.user_id)
    except JWTError:
        raise HTTPException(401, "Invalid token")

async def require_admin(
    user: UserDTO = Depends(get_current_user),
) -> UserDTO:
    if "admin" not in user.roles:
        raise HTTPException(403, "Admin required")
    return user
```

## Error Handling

```python
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://api.example.com/errors/{exc.error_type}",
            "title": exc.__class__.__name__,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )
```

## Testing Guidelines

- Use TestClient for endpoint tests
- Mock dependencies, not implementations
- Test validation errors
- Test authentication/authorization

## Common Mistakes

| Mistake | Solution |
|---------|----------|
| Business logic in routers | Move to use cases |
| Returning domain entities | Return DTOs |
| Direct database access | Use command/query bus |
| Missing validation | Use Pydantic models |
