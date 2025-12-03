# Requirements Document

## Introduction

Este documento define os requisitos para melhorias identificadas na análise do código em `src/interface/`, focando em aumentar a cobertura de testes HTTP reais, integrar middlewares órfãos, e melhorar a estrutura de testes para ItemExample e PedidoExample.

## Glossary

- **TestClient**: Cliente HTTP síncrono do FastAPI para testes de integração
- **AsyncClient**: Cliente HTTP assíncrono do httpx para testes async
- **ItemExample**: Entidade de exemplo para demonstração de CRUD de itens
- **PedidoExample**: Entidade de exemplo para demonstração de pedidos/orders
- **E2E Test**: Teste end-to-end que verifica o fluxo completo da aplicação
- **Property-Based Test**: Teste que verifica propriedades usando geração de dados aleatórios
- **Middleware**: Componente que processa requisições antes/depois dos handlers
- **RBAC**: Role-Based Access Control - controle de acesso baseado em papéis

## Análise de Gaps Identificados

### 1. Testes HTTP Reais Ausentes

Os testes atuais em `tests/integration/interface/` testam estruturas de DTOs e use cases com mocks, mas não fazem chamadas HTTP reais através do TestClient.

### 2. Middlewares Disponíveis mas Não Utilizados

| Middleware | Status | Motivo |
|------------|--------|--------|
| TimeoutMiddleware | ⚠️ Disponível | Implementação genérica, não HTTP-específica |
| FeatureFlagMiddleware | ⚠️ Disponível | Requer FeatureFlagEvaluator configurado |

### 3. Testes E2E para Examples Ausentes

Não existem testes E2E que testem o fluxo completo de ItemExample e PedidoExample via HTTP real.

## Requirements

### Requirement 1: Testes HTTP Reais para ItemExample

**User Story:** As a developer, I want real HTTP integration tests for ItemExample, so that I can verify the complete request/response cycle including middleware execution.

#### Acceptance Criteria

1. WHEN a GET request is made to /api/v1/examples/items via TestClient THEN the System SHALL return a paginated response with status 200
2. WHEN a POST request is made to /api/v1/examples/items with valid data and admin role THEN the System SHALL create the item and return status 201
3. WHEN a POST request is made to /api/v1/examples/items without WRITE permission THEN the System SHALL return status 403
4. WHEN a GET request is made to /api/v1/examples/items/{id} for non-existent item THEN the System SHALL return status 404
5. WHEN a DELETE request is made to /api/v1/examples/items/{id} without DELETE permission THEN the System SHALL return status 403

### Requirement 2: Testes HTTP Reais para PedidoExample

**User Story:** As a developer, I want real HTTP integration tests for PedidoExample, so that I can verify the complete order lifecycle via HTTP.

#### Acceptance Criteria

1. WHEN a GET request is made to /api/v1/examples/pedidos via TestClient THEN the System SHALL return a paginated response with status 200
2. WHEN a POST request is made to /api/v1/examples/pedidos with valid data THEN the System SHALL create the order and return status 201
3. WHEN a POST request is made to /api/v1/examples/pedidos/{id}/confirm THEN the System SHALL confirm the order and return status 200
4. WHEN a POST request is made to /api/v1/examples/pedidos/{id}/cancel with reason THEN the System SHALL cancel the order and return status 200
5. WHEN a request includes X-Tenant-Id header THEN the System SHALL filter results by tenant

### Requirement 3: Verificação de Middleware via HTTP

**User Story:** As a developer, I want to verify middleware execution through HTTP tests, so that I can ensure security headers and rate limiting are working.

#### Acceptance Criteria

1. WHEN any HTTP response is returned THEN the System SHALL include X-Request-ID header
2. WHEN any HTTP response is returned THEN the System SHALL include security headers (X-Frame-Options, X-Content-Type-Options)
3. WHEN rate limit is exceeded THEN the System SHALL return status 429 with Retry-After header
4. WHEN request body exceeds 10MB THEN the System SHALL return status 413

### Requirement 4: Testes E2E para Fluxo Completo

**User Story:** As a developer, I want E2E tests for complete ItemExample and PedidoExample workflows, so that I can verify the full business flow.

#### Acceptance Criteria

1. WHEN executing ItemExample lifecycle (create → read → update → delete) THEN the System SHALL complete all operations successfully
2. WHEN executing PedidoExample lifecycle (create → add items → confirm) THEN the System SHALL complete all operations successfully
3. WHEN executing PedidoExample cancellation flow (create → cancel) THEN the System SHALL complete all operations successfully
4. WHEN executing concurrent requests THEN the System SHALL handle them without data corruption

### Requirement 5: Documentação de Testes

**User Story:** As a developer, I want clear documentation on how to run tests manually, so that I can verify the API behavior.

#### Acceptance Criteria

1. WHEN reading test documentation THEN the System SHALL provide Docker commands for manual testing
2. WHEN reading test documentation THEN the System SHALL provide curl examples for all endpoints
3. WHEN reading test documentation THEN the System SHALL explain RBAC headers required
4. WHEN reading test documentation THEN the System SHALL document expected responses

