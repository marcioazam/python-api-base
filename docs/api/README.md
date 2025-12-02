# API Reference

## Visão Geral

A API REST do Python API Base segue os princípios RESTful e implementa padrões modernos de design de APIs.

## Base URL

```
Development: http://localhost:8000
Production:  https://api.example.com
```

## Autenticação

A API utiliza JWT (JSON Web Tokens) para autenticação.

### Obtendo Tokens

```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
}
```

### Usando Tokens

```http
GET /api/v1/users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

## Endpoints

### Health Checks

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health/live` | GET | Liveness probe |
| `/health/ready` | GET | Readiness probe |
| `/health/startup` | GET | Startup probe |

#### GET /health/live

```http
GET /health/live
```

**Response 200:**
```json
{
    "status": "healthy"
}
```

#### GET /health/ready

```http
GET /health/ready
```

**Response 200:**
```json
{
    "status": "healthy",
    "checks": {
        "database": "healthy",
        "redis": "healthy",
        "kafka": "healthy"
    },
    "version": "1.0.0",
    "uptime": 3600
}
```

---

### Authentication

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/auth/login` | POST | Login |
| `/api/v1/auth/logout` | POST | Logout |
| `/api/v1/auth/refresh` | POST | Refresh token |
| `/api/v1/auth/register` | POST | Registro |

#### POST /api/v1/auth/login

**Request:**
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response 200:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
}
```

**Response 401:**
```json
{
    "type": "https://api.example.com/errors/unauthorized",
    "title": "Unauthorized",
    "status": 401,
    "detail": "Invalid credentials"
}
```

---

### Users

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/users` | GET | Listar usuários |
| `/api/v1/users` | POST | Criar usuário |
| `/api/v1/users/{id}` | GET | Obter usuário |
| `/api/v1/users/{id}` | PUT | Atualizar usuário |
| `/api/v1/users/{id}` | DELETE | Deletar usuário |
| `/api/v1/users/me` | GET | Usuário atual |

#### GET /api/v1/users

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `skip` | int | 0 | Offset para paginação |
| `limit` | int | 100 | Limite de resultados |
| `sort_by` | string | created_at | Campo para ordenação |
| `order` | string | desc | Direção (asc/desc) |

**Response 200:**
```json
{
    "items": [
        {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 100,
    "skip": 0,
    "limit": 100
}
```

#### POST /api/v1/users

**Request:**
```json
{
    "email": "newuser@example.com",
    "name": "Jane Doe",
    "password": "SecureP@ss123"
}
```

**Response 201:**
```json
{
    "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "email": "newuser@example.com",
    "name": "Jane Doe",
    "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/v1/users/{id}

**Response 200:**
```json
{
    "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-16T14:20:00Z"
}
```

**Response 404:**
```json
{
    "type": "https://api.example.com/errors/not-found",
    "title": "Not Found",
    "status": 404,
    "detail": "User not found",
    "instance": "/api/v1/users/invalid-id"
}
```

---

### Items

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/items` | GET | Listar items |
| `/api/v1/items` | POST | Criar item |
| `/api/v1/items/{id}` | GET | Obter item |
| `/api/v1/items/{id}` | PUT | Atualizar item |
| `/api/v1/items/{id}` | DELETE | Deletar item |

#### GET /api/v1/items

**Query Parameters:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `skip` | int | 0 | Offset |
| `limit` | int | 100 | Limite |
| `name` | string | - | Filtro por nome |
| `min_price` | float | - | Preço mínimo |
| `max_price` | float | - | Preço máximo |

**Response 200:**
```json
{
    "items": [
        {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "Product A",
            "description": "Description",
            "price": 99.99,
            "created_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 50,
    "skip": 0,
    "limit": 100
}
```

---

## Error Responses

A API segue RFC 7807 (Problem Details for HTTP APIs).

### Formato de Erro

```json
{
    "type": "https://api.example.com/errors/{error-type}",
    "title": "Error Title",
    "status": 400,
    "detail": "Detailed error message",
    "instance": "/api/v1/resource/id",
    "errors": [
        {
            "field": "email",
            "message": "Invalid email format"
        }
    ]
}
```

### Códigos de Status

| Código | Descrição |
|--------|-----------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

---

## Rate Limiting

A API implementa rate limiting para proteção contra abuso.

### Headers de Resposta

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312800
```

### Response 429

```json
{
    "type": "https://api.example.com/errors/rate-limit",
    "title": "Too Many Requests",
    "status": 429,
    "detail": "Rate limit exceeded. Try again in 60 seconds.",
    "retry_after": 60
}
```

---

## Paginação

### Request

```http
GET /api/v1/items?skip=0&limit=20&sort_by=created_at&order=desc
```

### Response

```json
{
    "items": [...],
    "total": 100,
    "skip": 0,
    "limit": 20,
    "has_more": true
}
```

---

## Filtros

### Operadores Suportados

| Operador | Exemplo | Descrição |
|----------|---------|-----------|
| `eq` | `?status=active` | Igual |
| `ne` | `?status__ne=deleted` | Diferente |
| `gt` | `?price__gt=100` | Maior que |
| `gte` | `?price__gte=100` | Maior ou igual |
| `lt` | `?price__lt=100` | Menor que |
| `lte` | `?price__lte=100` | Menor ou igual |
| `in` | `?status__in=active,pending` | Em lista |
| `contains` | `?name__contains=test` | Contém |

---

## Versionamento

A API suporta versionamento via URL path.

```http
GET /api/v1/users    # Versão 1
GET /api/v2/users    # Versão 2
```

### Deprecation Headers

```http
Deprecation: true
Sunset: Sat, 31 Dec 2024 23:59:59 GMT
Link: </api/v2/users>; rel="successor-version"
```

---

## Métricas

### Endpoint

```http
GET /metrics
```

### Métricas Disponíveis

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/users",status="200"} 1234

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 900
http_request_duration_seconds_bucket{le="0.5"} 1100
http_request_duration_seconds_bucket{le="1.0"} 1200
```

---

## WebSocket

### Conexão

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'subscribe',
        channel: 'notifications'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

### Mensagens

```json
// Subscribe
{
    "type": "subscribe",
    "channel": "notifications"
}

// Notification
{
    "type": "notification",
    "data": {
        "id": "123",
        "message": "New item created"
    }
}
```

---

## GraphQL

### Endpoint

```http
POST /graphql
```

### Query

```graphql
query GetUser($id: ID!) {
    user(id: $id) {
        id
        email
        name
        createdAt
    }
}
```

### Mutation

```graphql
mutation CreateUser($input: CreateUserInput!) {
    createUser(input: $input) {
        id
        email
        name
    }
}
```

---

## SDKs

### Python

```python
from api_client import APIClient

client = APIClient(
    base_url="https://api.example.com",
    api_key="your-api-key"
)

users = client.users.list(limit=10)
user = client.users.create(email="test@example.com", name="Test")
```

### JavaScript

```javascript
import { APIClient } from '@example/api-client';

const client = new APIClient({
    baseUrl: 'https://api.example.com',
    apiKey: 'your-api-key'
});

const users = await client.users.list({ limit: 10 });
const user = await client.users.create({ email: 'test@example.com', name: 'Test' });
```
