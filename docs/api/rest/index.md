# REST API Documentation

## Overview

Python API Base exposes RESTful HTTP endpoints following REST principles and OpenAPI 3.1 specification.

## Base URL

```
http://localhost:8000/api/v{version}
```

## Authentication

All protected endpoints require JWT Bearer token:

```
Authorization: Bearer <access_token>
```

## API Versions

| Version | Base Path | Status |
|---------|-----------|--------|
| v1 | `/api/v1` | Stable |
| v2 | `/api/v2` | Experimental |

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe |

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/refresh` | Refresh token |
| POST | `/api/v1/auth/logout` | User logout |

### Users

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/users` | List users |
| POST | `/api/v1/users` | Create user |
| GET | `/api/v1/users/{id}` | Get user |
| PUT | `/api/v1/users/{id}` | Update user |
| DELETE | `/api/v1/users/{id}` | Delete user |

### Items

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/items` | List items |
| POST | `/api/v1/items` | Create item |
| GET | `/api/v1/items/{id}` | Get item |
| PUT | `/api/v1/items/{id}` | Update item |
| DELETE | `/api/v1/items/{id}` | Delete item |

## Request/Response Format

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes* | Bearer token |
| `Content-Type` | Yes | `application/json` |
| `X-Correlation-ID` | No | Request correlation ID |

### Response Format

```json
{
  "id": "string",
  "field": "value",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Error Response (RFC 7807)

```json
{
  "type": "https://api.example.com/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Resource not found",
  "instance": "/api/v1/users/123"
}
```

## Pagination

```
GET /api/v1/items?page=1&page_size=20
```

Response includes pagination metadata:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

## Related

- [Authentication](../security.md)
- [Error Handling](../../layers/interface/error-handling.md)
