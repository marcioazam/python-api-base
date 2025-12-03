# Error Types

## Overview

The error system provides a hierarchical set of exception classes following RFC 7807 Problem Details for HTTP APIs.

## Location

```
src/core/errors/
├── __init__.py
├── base/           # Base error classes
├── http/           # HTTP-specific errors
├── shared/         # Shared error utilities
└── status.py       # Status code mappings
```

## Error Hierarchy

```
BaseError
├── DomainError
│   ├── ValidationError
│   ├── BusinessRuleError
│   └── EntityNotFoundError
├── ApplicationError
│   ├── UseCaseError
│   └── AuthorizationError
├── InfrastructureError
│   ├── DatabaseError
│   ├── CacheError
│   ├── ExternalServiceError
│   └── MessagingError
└── InterfaceError
    ├── BadRequestError
    ├── UnauthorizedError
    ├── ForbiddenError
    └── NotFoundError
```

## Base Error

```python
class BaseError(Exception):
    """Base class for all application errors."""
    
    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
    
    def to_problem_detail(self) -> ProblemDetail:
        """Convert to RFC 7807 Problem Detail."""
        return ProblemDetail(
            type=f"https://api.example.com/errors/{self.code}",
            title=self.__class__.__name__,
            status=self.status_code,
            detail=self.message,
            instance=None,
            extensions=self.details,
        )
```

## Domain Errors

### ValidationError

```python
class ValidationError(DomainError):
    """Raised when validation fails."""
    
    status_code = 400
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, "value": value},
        )
```

### EntityNotFoundError

```python
class EntityNotFoundError(DomainError):
    """Raised when an entity is not found."""
    
    status_code = 404
    
    def __init__(
        self,
        entity_type: str,
        entity_id: str,
    ):
        super().__init__(
            message=f"{entity_type} with id {entity_id} not found",
            code="ENTITY_NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": entity_id},
        )
```

## Infrastructure Errors

### DatabaseError

```python
class DatabaseError(InfrastructureError):
    """Raised for database-related errors."""
    
    status_code = 500
    
    def __init__(
        self,
        message: str,
        operation: str | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={
                "operation": operation,
                "original_error": str(original_error) if original_error else None,
            },
        )
```

### ExternalServiceError

```python
class ExternalServiceError(InfrastructureError):
    """Raised when external service call fails."""
    
    status_code = 502
    
    def __init__(
        self,
        service_name: str,
        message: str,
        status_code: int | None = None,
    ):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            details={
                "service": service_name,
                "status_code": status_code,
            },
        )
```

## RFC 7807 Problem Details

### ProblemDetail Model

```python
@dataclass
class ProblemDetail:
    """RFC 7807 Problem Details."""
    
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    extensions: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        result = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        if self.instance:
            result["instance"] = self.instance
        result.update(self.extensions)
        return result
```

### Example Response

```json
{
  "type": "https://api.example.com/errors/VALIDATION_ERROR",
  "title": "ValidationError",
  "status": 400,
  "detail": "Email format is invalid",
  "instance": "/api/v1/users",
  "field": "email",
  "value": "invalid-email"
}
```

## Error Handling

### In Use Cases

```python
async def execute(self) -> Result[User, str]:
    user = await self.repository.get(self.user_id)
    if not user:
        raise EntityNotFoundError("User", self.user_id)
    return Ok(user)
```

### In Routers

```python
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        return await use_case.execute()
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.to_problem_detail().to_dict(),
        )
```

### Global Handler

```python
@app.exception_handler(BaseError)
async def base_error_handler(request: Request, exc: BaseError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_problem_detail().to_dict(),
    )
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `ENTITY_NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMITED` | 429 | Too many requests |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `EXTERNAL_SERVICE_ERROR` | 502 | External service failed |

## Related Documentation

- [Error Handling](../interface/error-handling.md)
- [Protocols](protocols.md)
