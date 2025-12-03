# API Endpoint: {Endpoint Name}

## Overview

Brief description of what this endpoint does.

## Endpoint

```
{METHOD} /api/v{version}/{path}
```

## Authentication

{Required | Optional | None}

**Required Permissions:** `{permission.action}`

## Request

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | Bearer token |
| `Content-Type` | Yes | `application/json` |

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `{param}` | string | Parameter description |

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `{param}` | string | No | `value` | Parameter description |

### Request Body

```json
{
  "field1": "string",
  "field2": 123,
  "field3": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field1` | string | Yes | Field description |
| `field2` | integer | No | Field description |
| `field3` | boolean | No | Field description |

## Response

### Success Response (200 OK)

```json
{
  "id": "string",
  "field1": "string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Resource identifier |
| `field1` | string | Field description |
| `created_at` | datetime | Creation timestamp |

### Error Responses

#### 400 Bad Request

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "Field validation failed",
  "instance": "/api/v1/resource"
}
```

#### 401 Unauthorized

```json
{
  "type": "https://api.example.com/errors/unauthorized",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Invalid or expired token"
}
```

#### 404 Not Found

```json
{
  "type": "https://api.example.com/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Resource not found"
}
```

## Examples

### cURL

```bash
curl -X {METHOD} \
  'https://api.example.com/api/v1/{path}' \
  -H 'Authorization: Bearer {token}' \
  -H 'Content-Type: application/json' \
  -d '{
    "field1": "value"
  }'
```

### Python

```python
import httpx

response = httpx.{method}(
    "https://api.example.com/api/v1/{path}",
    headers={"Authorization": f"Bearer {token}"},
    json={"field1": "value"}
)
```

## Related

- [Authentication](../operations/security.md)
- [Error Handling](../layers/interface/error-handling.md)
