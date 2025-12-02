"""OpenAPI 3.1 configuration and customization.

**Feature: enterprise-infrastructure-2025**
**Requirement: R5 - OpenAPI 3.1 Documentation**
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.openapi.utils import get_openapi

if TYPE_CHECKING:
    from fastapi import FastAPI


# API tags with descriptions
OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Health check endpoints for Kubernetes probes",
    },
    {
        "name": "Authentication",
        "description": "User authentication and authorization",
    },
    {
        "name": "Users",
        "description": "User management operations",
    },
    {
        "name": "Examples",
        "description": "Example domain operations (remove for production)",
        "externalDocs": {
            "description": "Example System Documentation",
            "url": "/docs/example-system-deactivation.md",
        },
    },
]


def custom_openapi(app: "FastAPI") -> dict:
    """Generate custom OpenAPI schema with enhanced documentation.

    **Requirement: R5.3 - JSON Schema with examples and descriptions**
    **Requirement: R5.4 - Request/response examples, error codes**

    Args:
        app: FastAPI application

    Returns:
        OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=_get_api_description(),
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token in Authorization header",
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service communication",
        },
    }

    # Add common response schemas
    openapi_schema["components"]["schemas"]["ProblemDetail"] = {
        "type": "object",
        "description": "RFC 7807 Problem Details",
        "properties": {
            "type": {
                "type": "string",
                "format": "uri",
                "description": "URI reference identifying the problem type",
                "example": "https://api.example.com/problems/validation-error",
            },
            "title": {
                "type": "string",
                "description": "Short, human-readable summary",
                "example": "Validation Error",
            },
            "status": {
                "type": "integer",
                "description": "HTTP status code",
                "example": 422,
            },
            "detail": {
                "type": "string",
                "description": "Human-readable explanation",
                "example": "One or more fields failed validation",
            },
            "instance": {
                "type": "string",
                "description": "URI reference to the specific occurrence",
                "example": "/api/v1/users",
            },
            "correlation_id": {
                "type": "string",
                "description": "Request correlation ID for tracing",
                "example": "abc-123-def-456",
            },
            "errors": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/ValidationErrorDetail"},
            },
        },
        "required": ["type", "title", "status"],
    }

    openapi_schema["components"]["schemas"]["ValidationErrorDetail"] = {
        "type": "object",
        "properties": {
            "field": {"type": "string", "example": "email"},
            "message": {"type": "string", "example": "Invalid email format"},
            "code": {"type": "string", "example": "invalid_format"},
        },
        "required": ["field", "message"],
    }

    # Add common responses
    openapi_schema["components"]["responses"] = {
        "BadRequest": {
            "description": "Bad Request",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                }
            },
        },
        "Unauthorized": {
            "description": "Unauthorized",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                }
            },
        },
        "Forbidden": {
            "description": "Forbidden",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                }
            },
        },
        "NotFound": {
            "description": "Not Found",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                }
            },
        },
        "ValidationError": {
            "description": "Validation Error",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                }
            },
        },
        "InternalServerError": {
            "description": "Internal Server Error",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                }
            },
        },
    }

    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        },
        {
            "url": "https://api.example.com",
            "description": "Production server",
        },
    ]

    # Add external docs
    openapi_schema["externalDocs"] = {
        "description": "API Documentation",
        "url": "https://github.com/your-org/python-api-base",
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _get_api_description() -> str:
    """Get API description for OpenAPI schema."""
    return """
# Python API Base

Modern REST API Framework with enterprise features.

## Features

- **Authentication**: JWT-based authentication with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Validation**: Request validation with RFC 7807 error responses
- **Caching**: Redis distributed cache with automatic invalidation
- **Storage**: MinIO S3-compatible object storage
- **Health**: Kubernetes-compatible health probes
- **Observability**: Structured logging, metrics, and tracing

## Error Handling

All errors follow RFC 7807 Problem Details format:

```json
{
  "type": "https://api.example.com/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more fields failed validation",
  "errors": [
    {"field": "email", "message": "Invalid email format"}
  ],
  "correlation_id": "abc-123"
}
```

## Authentication

Include JWT token in Authorization header:

```
Authorization: Bearer <token>
```

## Rate Limiting

API endpoints are rate limited. Check `X-RateLimit-*` headers:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Window reset time (Unix timestamp)
"""


def setup_openapi(app: "FastAPI") -> None:
    """Setup custom OpenAPI schema for the application.

    **Requirement: R5.1 - Swagger UI endpoint**
    **Requirement: R5.2 - ReDoc endpoint**

    Args:
        app: FastAPI application
    """
    app.openapi = lambda: custom_openapi(app)
