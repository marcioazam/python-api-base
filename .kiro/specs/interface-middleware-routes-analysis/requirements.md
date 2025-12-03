# Requirements Document

## Introduction

Este documento analisa a integração e conectividade dos módulos `src/interface/middleware` e `src/interface/routes` com o workflow do projeto, verificando bugs, conexões com o código, e possibilidade de testes com ItemExample e PedidoExample.

## Glossary

- **Middleware**: Componentes que processam requisições/respostas antes/depois dos handlers
- **Routes**: Endpoints da API que definem as operações disponíveis
- **ItemExample**: Entidade de exemplo para demonstração de CRUD
- **PedidoExample**: Entidade de exemplo para demonstração de pedidos/orders
- **RBAC**: Role-Based Access Control - controle de acesso baseado em papéis
- **Rate Limiting**: Limitação de taxa de requisições

## Análise de Integração

### 1. Estrutura de Middleware

#### 1.1 Middlewares Disponíveis

| Middleware | Localização | Status | Integrado em main.py |
|------------|-------------|--------|---------------------|
| SecurityHeadersMiddleware | security/security_headers.py | ✅ Funcional | ✅ Sim |
| CORSManager | security/cors_manager.py | ✅ Funcional | ✅ Via FastAPI CORS |
| RequestLoggerMiddleware | logging/request_logger.py | ✅ Funcional | ❌ Não diretamente |
| RequestIDMiddleware | request/request_id.py | ✅ Funcional | ❌ Não diretamente |
| TimeoutMiddleware | request/timeout.py | ✅ Funcional | ❌ Não diretamente |
| RequestSizeLimitMiddleware | request/request_size_limit.py | ✅ Funcional | ❌ Não diretamente |
| ResilienceMiddleware | production.py | ✅ Funcional | ✅ Sim |
| MultitenancyMiddleware | production.py | ✅ Funcional | ✅ Sim |
| AuditMiddleware | production.py | ✅ Funcional | ✅ Sim |
| FeatureFlagMiddleware | production.py | ✅ Funcional | ❌ Não (sem evaluator) |

#### 1.2 Middlewares Órfãos (Não Integrados)

Os seguintes middlewares existem mas NÃO são usados em `main.py`:
- `RequestLoggerMiddleware` - Usa `LoggingMiddleware` de infrastructure.observability
- `RequestIDMiddleware` - Não configurado
- `TimeoutMiddleware` - Não configurado
- `RequestSizeLimitMiddleware` - Não configurado
- `FeatureFlagMiddleware` - Não tem evaluator configurado

### 2. Estrutura de Routes

#### 2.1 Routes Disponíveis

| Router | Prefixo | Status | Integrado em main.py |
|--------|---------|--------|---------------------|
| health_router | /health | ✅ Funcional | ✅ Sim |
| auth_router | /api/v1 | ✅ Funcional | ✅ Sim |
| users_router | /api/v1 | ✅ Funcional | ✅ Sim |
| examples_router | /api/v1/examples | ✅ Funcional | ✅ Sim |
| infrastructure_router | /api/v1 | ✅ Funcional | ✅ Sim |
| enterprise_router | /api/v1 | ✅ Funcional | ✅ Sim |
| examples_v2_router | /api/v2/examples | ✅ Funcional | ✅ Sim |
| graphql_router | /api/graphql | ✅ Funcional | ✅ Condicional |

#### 2.2 Pasta routes/ - Análise

A pasta `src/interface/routes/` contém:
- `__init__.py` - Vazio (apenas docstring)
- `auth/` - Subpasta com constants.py e service.py

**PROBLEMA IDENTIFICADO**: A pasta `routes/` está praticamente vazia e não é usada diretamente. Os routers reais estão em `v1/` e `v2/`.

### 3. Conexão com ItemExample e PedidoExample

#### 3.1 Fluxo de Dados

```
Request → Middleware Stack → Router (v1/examples/router.py) → Use Case → Repository → Database
                                    ↓
                              ItemExampleUseCase / PedidoExampleUseCase
                                    ↓
                              ItemExampleRepository / PedidoExampleRepository
```

#### 3.2 Endpoints Disponíveis para ItemExample

| Método | Endpoint | Descrição | RBAC |
|--------|----------|-----------|------|
| GET | /api/v1/examples/items | Listar items | Não |
| POST | /api/v1/examples/items | Criar item | WRITE |
| GET | /api/v1/examples/items/{id} | Obter item | Não |
| PUT | /api/v1/examples/items/{id} | Atualizar item | WRITE |
| DELETE | /api/v1/examples/items/{id} | Deletar item | DELETE |

#### 3.3 Endpoints Disponíveis para PedidoExample

| Método | Endpoint | Descrição | RBAC |
|--------|----------|-----------|------|
| GET | /api/v1/examples/pedidos | Listar pedidos | Não |
| POST | /api/v1/examples/pedidos | Criar pedido | WRITE |
| GET | /api/v1/examples/pedidos/{id} | Obter pedido | Não |
| POST | /api/v1/examples/pedidos/{id}/items | Adicionar item | Não |
| POST | /api/v1/examples/pedidos/{id}/confirm | Confirmar | Não |
| POST | /api/v1/examples/pedidos/{id}/cancel | Cancelar | Não |

### 4. Testes Existentes

#### 4.1 Testes de Integração

- `tests/integration/examples/test_item_api.py` - Testa estrutura de commands/queries
- `tests/integration/examples/test_pedido_api.py` - Testa estrutura de commands/queries

**PROBLEMA**: Os testes existentes NÃO testam a API HTTP real, apenas estruturas de dados.

#### 4.2 Testes Unitários

- `tests/unit/test_health.py` - Usa TestClient mas está skipado

### 5. Docker - Possibilidade de Teste Manual

#### 5.1 Comandos para Subir

```bash
# Desenvolvimento com hot reload
cd deployments/docker
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up

# Com infraestrutura completa (Kafka, MinIO, etc)
docker compose -f docker-compose.base.yml -f docker-compose.infra.yml up
```

#### 5.2 Endpoints para Teste Manual

Após subir a API em http://localhost:8000:

```bash
# Health check
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Listar items
curl http://localhost:8000/api/v1/examples/items

# Criar item (requer header X-User-Roles: admin ou editor)
curl -X POST http://localhost:8000/api/v1/examples/items \
  -H "Content-Type: application/json" \
  -H "X-User-Roles: admin" \
  -d '{"name": "Test Item", "sku": "TEST-001", "price_amount": 99.99, "price_currency": "BRL", "quantity": 10}'

# Listar pedidos
curl http://localhost:8000/api/v1/examples/pedidos

# Criar pedido
curl -X POST http://localhost:8000/api/v1/examples/pedidos \
  -H "Content-Type: application/json" \
  -H "X-User-Roles: admin" \
  -d '{"customer_id": "cust-123", "customer_name": "John Doe", "customer_email": "john@example.com"}'
```

## Requirements

### Requirement 1: Middleware Integration Analysis

**User Story:** As a developer, I want to understand which middlewares are integrated and which are orphaned, so that I can ensure all security and logging features are active.

#### Acceptance Criteria

1. WHEN the application starts THEN the System SHALL load SecurityHeadersMiddleware with CSP, X-Frame-Options, and HSTS headers
2. WHEN the application starts THEN the System SHALL load ResilienceMiddleware with circuit breaker pattern
3. WHEN the application starts THEN the System SHALL load MultitenancyMiddleware for tenant context
4. WHEN the application starts THEN the System SHALL load AuditMiddleware for request audit trail
5. IF RequestLoggerMiddleware is not integrated THEN the System SHALL document this as a gap

### Requirement 2: Routes Connectivity Verification

**User Story:** As a developer, I want to verify that all routes are properly connected to the application, so that I can ensure API endpoints are accessible.

#### Acceptance Criteria

1. WHEN a GET request is made to /api/v1/examples/items THEN the System SHALL return a paginated list of ItemExample entities
2. WHEN a POST request is made to /api/v1/examples/items with valid data and WRITE permission THEN the System SHALL create a new ItemExample
3. WHEN a GET request is made to /api/v1/examples/pedidos THEN the System SHALL return a paginated list of PedidoExample entities
4. WHEN a POST request is made to /api/v1/examples/pedidos with valid data and WRITE permission THEN the System SHALL create a new PedidoExample

### Requirement 3: Test Coverage for API Endpoints

**User Story:** As a developer, I want integration tests that actually test the HTTP API, so that I can verify the full request/response cycle.

#### Acceptance Criteria

1. WHEN running integration tests THEN the System SHALL test ItemExample CRUD operations via HTTP
2. WHEN running integration tests THEN the System SHALL test PedidoExample CRUD operations via HTTP
3. WHEN running integration tests THEN the System SHALL verify middleware execution (headers, rate limiting)
4. WHEN running integration tests THEN the System SHALL verify RBAC enforcement

### Requirement 4: Docker Testing Capability

**User Story:** As a developer, I want to be able to test the API manually using Docker, so that I can verify the full stack integration.

#### Acceptance Criteria

1. WHEN docker-compose.dev.yml is executed THEN the System SHALL start the API with hot reload
2. WHEN the API container starts THEN the System SHALL connect to PostgreSQL and Redis
3. WHEN the API is running THEN the System SHALL expose endpoints on port 8000
4. WHEN health endpoints are called THEN the System SHALL return appropriate status

## Problemas Identificados

### P1: Pasta routes/ Subutilizada
- **Severidade**: Baixa
- **Descrição**: A pasta `src/interface/routes/` contém apenas auth/constants.py e auth/service.py, mas não é usada como router principal
- **Impacto**: Confusão na estrutura do projeto
- **Recomendação**: Mover conteúdo para v1/auth/ ou documentar propósito

### P2: Middlewares Não Integrados
- **Severidade**: Média
- **Descrição**: RequestLoggerMiddleware, RequestIDMiddleware, TimeoutMiddleware não estão integrados
- **Impacto**: Funcionalidades de logging e timeout não ativas
- **Recomendação**: Integrar ou remover código morto

### P3: Testes de Integração Incompletos
- **Severidade**: Alta
- **Descrição**: Testes existentes não testam a API HTTP real
- **Impacto**: Falta de cobertura de testes E2E
- **Recomendação**: Criar testes com TestClient que testem endpoints reais

### P4: FeatureFlagMiddleware Sem Evaluator
- **Severidade**: Baixa
- **Descrição**: Middleware existe mas não é configurado com evaluator
- **Impacto**: Feature flags não funcionais
- **Recomendação**: Configurar ou documentar como opcional

## Conclusão

O código em `src/interface/middleware` e `src/interface/routes` está **parcialmente integrado** ao workflow:

✅ **Funcionando**:
- Routers de examples (v1 e v2) estão conectados
- ItemExample e PedidoExample são acessíveis via API
- Middlewares de produção (Resilience, Multitenancy, Audit) estão ativos
- Docker está configurado para testes manuais

❌ **Gaps**:
- Alguns middlewares não estão integrados
- Testes de integração não testam HTTP real
- Pasta routes/ está subutilizada
