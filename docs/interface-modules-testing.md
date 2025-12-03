# Interface Modules Testing Guide

Este guia descreve como testar manualmente os módulos `interface/versioning`, `interface/errors` e `interface/graphql` usando Docker e exemplos de requisições.

## Pré-requisitos

- Docker e Docker Compose instalados
- curl ou Postman para requisições HTTP

## Iniciando a API via Docker

### Desenvolvimento (com hot reload)

```bash
cd deployments/docker
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up
```

### Produção

```bash
cd deployments/docker
docker compose -f docker-compose.base.yml -f docker-compose.production.yml up -d
```

### Com infraestrutura completa (Kafka, RabbitMQ, etc.)

```bash
cd deployments/docker
docker compose -f docker-compose.base.yml -f docker-compose.infra.yml up -d
```

## Endpoints Disponíveis

| Endpoint | Descrição |
|----------|-----------|
| `http://localhost:8000/health/live` | Health check |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/api/v1/examples/*` | API v1 |
| `http://localhost:8000/api/v2/examples/*` | API v2 (versionada) |
| `http://localhost:8000/api/graphql` | GraphQL endpoint |

## Testando GraphQL

### Acessando GraphQL Playground

Acesse `http://localhost:8000/api/graphql` no navegador para usar o GraphQL Playground interativo.

### Queries para ItemExample

#### Buscar item por ID

```graphql
query GetItem {
  item(id: "item-123") {
    id
    name
    description
    category
    price
    quantity
    status
    createdAt
    updatedAt
  }
}
```

#### Listar items com paginação

```graphql
query ListItems {
  items(first: 10, after: null, category: null) {
    edges {
      node {
        id
        name
        category
        price
        quantity
        status
      }
      cursor
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    totalCount
  }
}
```

### Queries para PedidoExample

#### Buscar pedido por ID

```graphql
query GetPedido {
  pedido(id: "pedido-123") {
    id
    customerId
    status
    items {
      itemId
      quantity
      unitPrice
    }
    total
    createdAt
    confirmedAt
    cancelledAt
  }
}
```

#### Listar pedidos com paginação

```graphql
query ListPedidos {
  pedidos(first: 10, after: null, customerId: null) {
    edges {
      node {
        id
        customerId
        status
        total
        createdAt
      }
      cursor
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    totalCount
  }
}
```

### Mutations para ItemExample

#### Criar item

```graphql
mutation CreateItem {
  createItem(input: {
    name: "Novo Item"
    description: "Descrição do item"
    category: "electronics"
    price: 99.99
    quantity: 10
  }) {
    success
    item {
      id
      name
      category
      price
      quantity
      status
      createdAt
    }
    error
  }
}
```

#### Atualizar item

```graphql
mutation UpdateItem {
  updateItem(id: "item-123", input: {
    name: "Item Atualizado"
    price: 149.99
    quantity: 5
  }) {
    success
    item {
      id
      name
      price
      quantity
      updatedAt
    }
    error
  }
}
```

#### Deletar item

```graphql
mutation DeleteItem {
  deleteItem(id: "item-123") {
    success
    message
  }
}
```

### Mutations para PedidoExample

#### Criar pedido

```graphql
mutation CreatePedido {
  createPedido(input: {
    customerId: "customer-123"
  }) {
    success
    pedido {
      id
      customerId
      status
      total
      createdAt
    }
    error
  }
}
```

#### Confirmar pedido

```graphql
mutation ConfirmPedido {
  confirmPedido(id: "pedido-123") {
    success
    pedido {
      id
      status
      confirmedAt
    }
    error
  }
}
```

## Testando API REST v2

### Listar items (v2)

```bash
curl -X GET "http://localhost:8000/api/v2/examples/items?page=1&page_size=10" \
  -H "Accept: application/json"
```

Resposta esperada:
```json
{
  "items": [
    {
      "id": "item-123",
      "name": "Item Example",
      "description": "Description",
      "category": "electronics",
      "price": 99.99,
      "quantity": 10,
      "status": "active",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

### Buscar item por ID (v2)

```bash
curl -X GET "http://localhost:8000/api/v2/examples/items/item-123" \
  -H "Accept: application/json"
```

Resposta esperada:
```json
{
  "data": {
    "id": "item-123",
    "name": "Item Example",
    "description": "Description",
    "category": "electronics",
    "price": 99.99,
    "quantity": 10,
    "status": "active",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": null
  }
}
```

### Criar item (v2)

```bash
curl -X POST "http://localhost:8000/api/v2/examples/items" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "Novo Item",
    "description": "Descrição do item",
    "category": "electronics",
    "price": 99.99,
    "quantity": 10
  }'
```

Resposta esperada (status 201):
```json
{
  "data": {
    "id": "generated-uuid",
    "name": "Novo Item",
    "description": "Descrição do item",
    "category": "electronics",
    "price": 99.99,
    "quantity": 10,
    "status": "active",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": null
  },
  "status_code": 201
}
```

### Listar pedidos (v2)

```bash
curl -X GET "http://localhost:8000/api/v2/examples/pedidos?page=1&page_size=10" \
  -H "Accept: application/json"
```

### Buscar pedido por ID (v2)

```bash
curl -X GET "http://localhost:8000/api/v2/examples/pedidos/pedido-123" \
  -H "Accept: application/json"
```

## Testando Error Handling

### Recurso não encontrado (404)

```bash
curl -X GET "http://localhost:8000/api/v2/examples/items/non-existent-id" \
  -H "Accept: application/json"
```

Resposta esperada:
```json
{
  "detail": "Item non-existent-id not found"
}
```

### Erro de validação (422)

```bash
curl -X POST "http://localhost:8000/api/v2/examples/items" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "",
    "category": "",
    "price": -1
  }'
```

## Executando Testes Automatizados

### Todos os testes de integração

```bash
pytest tests/integration/interface/ -v
```

### Testes de propriedades

```bash
pytest tests/properties/test_interface_*.py -v
```

### Testes específicos

```bash
# GraphQL
pytest tests/integration/interface/test_graphql_integration.py -v

# Versioning
pytest tests/integration/interface/test_versioning_integration.py -v

# Errors
pytest tests/integration/interface/test_errors_integration.py -v
```

## Correções Aplicadas (2025-12-03)

Durante a análise de integração, foram identificados e corrigidos os seguintes bugs:

1. **PaginatedResponse field name**: O campo `page_size` foi corrigido para `size` em todos os routers (v1 e v2) para corresponder ao modelo `PaginatedResponse` definido em `application/common/base/dto.py`.

2. **V2 Router - Métodos de repositório**: O router v2 foi atualizado para usar os Use Cases (`ItemExampleUseCase`, `PedidoExampleUseCase`) em vez de acessar diretamente os repositórios, garantindo consistência com o padrão do v1.

3. **V2 Router - Integração com Kafka**: Adicionada integração com `EventPublisher` para publicação de eventos Kafka, seguindo o mesmo padrão do v1.

## Troubleshooting

### GraphQL não disponível

Se o endpoint `/api/graphql` retornar 404, verifique:

1. Se `strawberry-graphql[fastapi]` está instalado:
   ```bash
   pip show strawberry-graphql
   ```

2. Se `HAS_STRAWBERRY` é `True`:
   ```python
   from interface.graphql import HAS_STRAWBERRY
   print(HAS_STRAWBERRY)
   ```

3. Logs da aplicação:
   ```bash
   docker compose logs -f api
   ```

### Banco de dados não conectado

```bash
# Verificar se PostgreSQL está rodando
docker compose exec postgres pg_isready -U postgres

# Verificar conexão
docker compose logs postgres
```

### Limpar e reiniciar

```bash
# Parar e remover containers
docker compose down -v

# Reconstruir imagens
docker compose build --no-cache

# Iniciar novamente
docker compose up
```
