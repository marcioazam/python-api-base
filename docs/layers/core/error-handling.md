# Error Handling

## Overview

O sistema implementa tratamento de erros seguindo RFC 7807 (Problem Details for HTTP APIs), fornecendo respostas de erro estruturadas e consistentes.

## RFC 7807 Problem Details

```json
{
    "type": "https://api.example.com/errors/validation",
    "title": "Validation Error",
    "status": 422,
    "detail": "The request body contains invalid data",
    "instance": "/api/v1/users",
    "errors": [
        {
            "field": "email",
            "message": "Invalid email format"
        }
    ]
}
```

## Exception Hierarchy

```python
# Base exceptions
class AppError(Exception):
    """Base application error."""
    status_code: int = 500
    error_type: str = "internal_error"
    
    def __init__(self, detail: str, **kwargs):
        self.detail = detail
        self.extra = kwargs
        super().__init__(detail)

# Domain errors
class DomainError(AppError):
    """Domain layer errors."""
    status_code = 400

class ValidationError(DomainError):
    """Validation failed."""
    error_type = "validation_error"
    status_code = 422

class NotFoundError(DomainError):
    """Entity not found."""
    error_type = "not_found"
    status_code = 404

class ConflictError(DomainError):
    """Resource conflict."""
    error_type = "conflict"
    status_code = 409

# Auth errors
class AuthError(AppError):
    """Authentication/Authorization errors."""
    status_code = 401

class UnauthorizedError(AuthError):
    """Not authenticated."""
    error_type = "unauthorized"

class ForbiddenError(AuthError):
    """Not authorized."""
    error_type = "forbidden"
    status_code = 403

# Infrastructure errors
class InfrastructureError(AppError):
    """Infrastructure layer errors."""
    status_code = 503

class DatabaseError(InfrastructureError):
    """Database errors."""
    error_type = "database_error"

class CacheError(InfrastructureError):
    """Cache errors."""
    error_type = "cache_error"
```

## FastAPI Exception Handlers

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

def setup_exception_handlers(app: FastAPI) -> None:
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
                **exc.extra,
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "type": "https://api.example.com/errors/validation",
                "title": "Validation Error",
                "status": 422,
                "detail": "Request validation failed",
                "instance": str(request.url.path),
                "errors": [
                    {
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                    }
                    for err in exc.errors()
                ],
            },
        )
```

## Usage in Code

```python
# In domain/application layer
async def get_user(user_id: str) -> User:
    user = await repository.get(user_id)
    if user is None:
        raise NotFoundError(
            detail=f"User with id '{user_id}' not found",
            entity_type="User",
            entity_id=user_id,
        )
    return user

# In use case
async def create_user(email: str) -> User:
    if await repository.exists_by_email(email):
        raise ConflictError(
            detail=f"User with email '{email}' already exists",
            field="email",
        )
    # ...
```

## Result Pattern (Alternative)

```python
from result import Result, Ok, Err

async def create_user(data: CreateUserDTO) -> Result[User, str]:
    if await repository.exists_by_email(data.email):
        return Err("Email already exists")
    
    user = User(...)
    created = await repository.create(user)
    return Ok(created)

# Usage
result = await create_user(data)
if result.is_err():
    raise ConflictError(detail=result.error)
return result.value
```

## Logging Errors

```python
import structlog

logger = structlog.get_logger()

@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://api.example.com/errors/internal",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred",
            "instance": str(request.url.path),
        },
    )
```
