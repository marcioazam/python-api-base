# ADR-010: Error Handling (RFC 7807)

## Status
Accepted

## Context

The system needs consistent error handling that:
- Provides machine-readable error responses
- Includes sufficient detail for debugging
- Follows industry standards
- Supports internationalization

## Decision

We implement RFC 7807 (Problem Details for HTTP APIs):

### Response Format

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
            "message": "Invalid email format",
            "code": "INVALID_FORMAT"
        }
    ],
    "trace_id": "abc123"
}
```

### Exception Hierarchy

```python
# src/infrastructure/exceptions.py
class InfrastructureError(Exception):
    """Base infrastructure exception."""
    status_code: int = 500
    error_type: str = "internal_error"

class DatabaseError(InfrastructureError):
    status_code = 503
    error_type = "database_error"

class CacheError(InfrastructureError):
    status_code = 503
    error_type = "cache_error"

class ExternalServiceError(InfrastructureError):
    status_code = 502
    error_type = "external_service_error"

# src/core/errors/exceptions.py
class DomainError(Exception):
    """Base domain exception."""

class ValidationError(DomainError):
    status_code = 422
    error_type = "validation_error"

class NotFoundError(DomainError):
    status_code = 404
    error_type = "not_found"

class UnauthorizedError(DomainError):
    status_code = 401
    error_type = "unauthorized"

class ForbiddenError(DomainError):
    status_code = 403
    error_type = "forbidden"

class ConflictError(DomainError):
    status_code = 409
    error_type = "conflict"
```

### Exception Handlers

```python
# src/core/errors/exception_handlers.py
@app.exception_handler(DomainError)
async def domain_error_handler(
    request: Request,
    exc: DomainError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://api.example.com/errors/{exc.error_type}",
            "title": exc.__class__.__name__,
            "status": exc.status_code,
            "detail": str(exc),
            "instance": str(request.url.path),
            "trace_id": get_trace_id(),
        },
    )
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `validation_error` | 422 | Invalid input data |
| `not_found` | 404 | Resource not found |
| `unauthorized` | 401 | Authentication required |
| `forbidden` | 403 | Insufficient permissions |
| `conflict` | 409 | Resource conflict |
| `rate_limited` | 429 | Too many requests |
| `internal_error` | 500 | Server error |
| `database_error` | 503 | Database unavailable |
| `external_service_error` | 502 | External service failed |

## Consequences

### Positive
- Consistent error format
- Machine-readable responses
- Trace ID for debugging
- Standard compliance

### Negative
- More verbose than simple messages
- Requires client adaptation

### Neutral
- Error types documented in OpenAPI
- Supports error aggregation

## Alternatives Considered

1. **Simple JSON errors** - Rejected as not standardized
2. **GraphQL errors** - Rejected as REST-focused
3. **Custom error format** - Rejected in favor of RFC standard

## References

- [src/core/errors/exception_handlers.py](../../src/core/errors/exception_handlers.py)
- [src/infrastructure/exceptions.py](../../src/infrastructure/exceptions.py)
- [RFC 7807 - Problem Details for HTTP APIs](https://tools.ietf.org/html/rfc7807)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
