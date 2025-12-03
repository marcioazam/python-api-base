# Manual API Testing Guide

**Feature: src-interface-improvements**
**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

## Overview

Este guia documenta como testar manualmente a API usando Docker e curl.

## Docker Commands

### Subir a API em Desenvolvimento

```bash
# Navegar para o diretório de deployments
cd deployments/docker

# Subir com hot reload (desenvolvimento)
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up

# Subir em background
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d

# Ver logs
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml logs -f api

# Parar
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml down
```

### Subir com Infraestrutura Completa

```bash
# Com Kafka, MinIO, etc.
docker compose -f docker-compose.base.yml -f docker-compose.infra.yml up
```

## RBAC Headers

A API usa headers HTTP para autenticação e autorização:

| Header | Descrição | Valores |
|--------|-----------|---------|
| `X-User-Id` | ID do usuário | Qualquer string |
| `X-User-Roles` | Roles do usuário (separadas por vírgula) | `admin`, `editor`, `user`, `viewer` |
| `X-Tenant-Id` | ID do tenant (multi-tenancy) | Qualquer string |

### Permissões por Role

| Role | READ | WRITE | DELETE |
|------|------|-------|--------|
| `admin` | ✅ | ✅ | ✅ |
| `editor` | ✅ | ✅ | ❌ |
| `user` | ✅ | ✅ | ❌ |
| `moderator` | ✅ | ✅ | ❌ |
| `viewer` | ✅ | ❌ | ❌ |

## Curl Examples

### Health Check

```bash
# Liveness (sempre disponível)
curl http://localhost:8000/health/live

# Readiness (verifica dependências)
curl http://localhost:8000/health/ready
```

**Resposta esperada (liveness):**
```json
{"status": "ok"}
```

### ItemExample Endpoints

#### Listar Items

```bash
curl -X GET "http://localhost:8000/api/v1/examples/items" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin"
```

**Resposta esperada:**
```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "size": 20
}
```

#### Criar Item (requer WRITE permission)

```bash
curl -X POST "http://localhost:8000/api/v1/examples/items" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin" \
  -d '{
    "name": "Test Item",
    "sku": "TEST-001",
    "price": {"amount": "99.99", "currency": "BRL"},
    "quantity": 10,
    "category": "electronics",
    "tags": ["new", "featured"]
  }'
```

**Resposta esperada (201 Created):**
```json
{
  "data": {
    "id": "item-uuid",
    "name": "Test Item",
    "sku": "TEST-001",
    "price": {"amount": "99.99", "currency": "BRL"},
    "quantity": 10,
    "category": "electronics",
    "status": "active",
    "tags": ["new", "featured"]
  },
  "status_code": 201
}
```

#### Obter Item por ID

```bash
curl -X GET "http://localhost:8000/api/v1/examples/items/{item_id}" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin"
```

#### Atualizar Item (requer WRITE permission)

```bash
curl -X PUT "http://localhost:8000/api/v1/examples/items/{item_id}" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin" \
  -d '{
    "name": "Updated Item Name",
    "quantity": 20
  }'
```

#### Deletar Item (requer DELETE permission)

```bash
curl -X DELETE "http://localhost:8000/api/v1/examples/items/{item_id}" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin"
```

**Resposta esperada (204 No Content):** Sem corpo

### PedidoExample Endpoints

#### Listar Pedidos

```bash
curl -X GET "http://localhost:8000/api/v1/examples/pedidos" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin" \
  -H "X-Tenant-Id: tenant-123"
```

#### Criar Pedido

```bash
curl -X POST "http://localhost:8000/api/v1/examples/pedidos" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin" \
  -H "X-Tenant-Id: tenant-123" \
  -d '{
    "customer_id": "cust-123",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "shipping_address": "123 Main St",
    "notes": "Rush order"
  }'
```

**Resposta esperada (201 Created):**
```json
{
  "data": {
    "id": "pedido-uuid",
    "customer_id": "cust-123",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "status": "pending",
    "items": [],
    "total_amount": "0.00"
  },
  "status_code": 201
}
```

#### Confirmar Pedido

```bash
curl -X POST "http://localhost:8000/api/v1/examples/pedidos/{pedido_id}/confirm" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin"
```

**Resposta esperada:**
```json
{
  "data": {
    "id": "pedido-uuid",
    "status": "confirmed"
  }
}
```

#### Cancelar Pedido

```bash
curl -X POST "http://localhost:8000/api/v1/examples/pedidos/{pedido_id}/cancel" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -H "X-User-Roles: admin" \
  -d '{
    "reason": "Customer requested cancellation"
  }'
```

**Resposta esperada:**
```json
{
  "data": {
    "id": "pedido-uuid",
    "status": "cancelled"
  }
}
```

## Error Responses

### 403 Forbidden (Missing Permission)

```json
{
  "detail": "Permission 'write' required. User roles: ['viewer']"
}
```

### 404 Not Found

```json
{
  "detail": "ItemExample item-123 not found"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 429 Rate Limit Exceeded

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

## Security Headers

Todas as respostas incluem os seguintes headers de segurança:

| Header | Valor |
|--------|-------|
| `X-Request-ID` | UUID único da requisição |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

## Running Automated Tests

```bash
# Todos os testes E2E
pytest tests/e2e/ -v

# Testes de ItemExample
pytest tests/e2e/examples/test_items_http_real.py -v

# Testes de PedidoExample
pytest tests/e2e/examples/test_pedidos_http_real.py -v

# Testes de Middleware
pytest tests/e2e/examples/test_middleware_http.py -v

# Testes de Propriedade
pytest tests/properties/test_http_properties.py -v
```

