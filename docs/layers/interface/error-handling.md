# Error Handling

## Overview

Error handling follows RFC 7807 Problem Details for HTTP APIs, providing consistent, machine-readable error responses.

## RFC 7807 Format

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
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

## Problem Detail Model

```python
@dataclass
class ProblemDetail:
    """RFC 7807 Problem Details."""
    
    type: str           # URI reference identifying error type
    title: str          # Short, human-readable summary
    status: int         # HTTP status code
    detail: str         # Human-readable explanation
    instance: str | None = None  # URI reference to specific occurrence
    
    def to_dict(self) -> dict:
        result = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        if self.instance:
            result["instance"] = self.instance
        return result
```

## Error Handler

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(BaseError)
async def base_error_handler(
    request: Request,
    exc: BaseError,
) -> JSONResponse:
    """Handle application errors."""
    problem = ProblemDetail(
        type=f"https://api.example.com/errors/{exc.code}",
        title=exc.__class__.__name__,
        status=exc.status_code,
        detail=exc.message,
        instance=str(request.url.path),
    )
    
    response_data = problem.to_dict()
    response_data.update(exc.details)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        media_type="application/problem+json",
    )

@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://api.example.com/errors/validation-error",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request validation failed",
            "instance": str(request.url.path),
            "errors": errors,
        },
        media_type="application/problem+json",
    )
```

## Error Types

| Error | Status | Type URI |
|-------|--------|----------|
| ValidationError | 400 | `/errors/validation-error` |
| UnauthorizedError | 401 | `/errors/unauthorized` |
| ForbiddenError | 403 | `/errors/forbidden` |
| NotFoundError | 404 | `/errors/not-found` |
| ConflictError | 409 | `/errors/conflict` |
| RateLimitError | 429 | `/errors/rate-limited` |
| InternalError | 500 | `/errors/internal-error` |
| ServiceUnavailable | 503 | `/errors/service-unavailable` |

## Error Response Examples

### Validation Error (400)

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Request validation failed",
  "instance": "/api/v1/users",
  "errors": [
    {
      "field": "email",
      "message": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### Unauthorized (401)

```json
{
  "type": "https://api.example.com/errors/unauthorized",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Invalid or expired token",
  "instance": "/api/v1/users/me"
}
```

### Not Found (404)

```json
{
  "type": "https://api.example.com/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "User with id '123' not found",
  "instance": "/api/v1/users/123",
  "entity_type": "User",
  "entity_id": "123"
}
```

### Rate Limited (429)

```json
{
  "type": "https://api.example.com/errors/rate-limited",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "instance": "/api/v1/users",
  "retry_after": 60
}
```

## Usage in Routers

```python
@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    use_case: GetUserUseCase = Depends(get_use_case),
) -> UserResponse:
    user = await use_case.execute(user_id)
    
    if not user:
        raise NotFoundError(
            entity_type="User",
            entity_id=user_id,
        )
    
    return UserResponse.from_entity(user)

@router.post("/users")
async def create_user(
    data: UserCreateRequest,
    use_case: CreateUserUseCase = Depends(get_use_case),
) -> UserResponse:
    result = await use_case.execute(data)
    
    if result.is_err:
        error = result.unwrap_err()
        if "email" in error.lower():
            raise ConflictError(
                message=error,
                details={"field": "email"},
            )
        raise ValidationError(message=error)
    
    return UserResponse.from_entity(result.unwrap())
```

## Related Documentation

- [Error Types](../core/errors.md)
- [Middleware](middleware.md)
- [API Documentation](../../api/index.md)
