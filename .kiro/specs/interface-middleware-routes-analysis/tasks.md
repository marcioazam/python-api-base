# Implementation Plan

## Task Overview

Este plano implementa as correções e melhorias para `src/interface/middleware` e `src/interface/routes`, incluindo integração de middlewares, reorganização de estrutura, e criação de testes HTTP reais.

---

- [x] 1. Integrar Middlewares Órfãos em main.py
  - [x] 1.1 Adicionar RequestIDMiddleware como primeiro middleware
    - Importar de `interface.middleware.request`
    - Configurar antes de LoggingMiddleware
    - _Requirements: 1.1_
  - [x] 1.2 Adicionar RequestLoggerMiddleware após LoggingMiddleware
    - Configurar paths excluídos (health, metrics, docs)
    - _Requirements: 1.1_
  - [x] 1.3 Adicionar TimeoutMiddleware com timeout configurável
    - Default: 30 segundos (via ResilienceMiddleware)
    - Configurar via settings
    - _Requirements: 1.1_
  - [x] 1.4 Adicionar RequestSizeLimitMiddleware
    - Default: 10MB
    - Configurar via settings
    - _Requirements: 1.1_
  - [x] 1.5 Write property test for middleware integration
    - **Property 1: Security Headers Present**
    - **Validates: Requirements 1.1**

- [x] 2. Reorganizar Pasta routes/
  - [x] 2.1 Atualizar src/interface/routes/__init__.py
    - Exportar componentes de auth
    - Adicionar docstring explicativa
    - _Requirements: 2.1_
  - [x] 2.2 Criar README.md em src/interface/routes/
    - Documentar estrutura e propósito
    - Explicar relação com v1/ e v2/
    - _Requirements: 2.1_

- [x] 3. Checkpoint - Verificar middlewares integrados
  - All tests pass ✅

- [x] 4. Criar Testes de Integração HTTP para ItemExample
  - [x] 4.1 Criar tests/integration/interface/test_items_api_http.py
    - Setup com AsyncClient
    - Fixtures para headers de autenticação
    - _Requirements: 2.1, 2.2_
  - [x] 4.2 Implementar teste GET /api/v1/examples/items
    - Verificar estrutura de paginação
    - Verificar campos obrigatórios
    - _Requirements: 2.1_
  - [x] 4.3 Implementar teste POST /api/v1/examples/items
    - Testar criação com dados válidos
    - Verificar resposta 201
    - _Requirements: 2.2_
  - [x] 4.4 Implementar teste GET /api/v1/examples/items/{id}
    - Testar leitura de item existente
    - Testar 404 para item inexistente
    - _Requirements: 2.1_
  - [x] 4.5 Implementar teste PUT /api/v1/examples/items/{id}
    - Testar atualização com dados válidos
    - Verificar RBAC enforcement
    - _Requirements: 2.2_
  - [x] 4.6 Implementar teste DELETE /api/v1/examples/items/{id}
    - Testar deleção com permissão
    - Verificar 403 sem permissão
    - _Requirements: 2.2_
  - [x] 4.7 Write property test for pagination
    - **Property 2: Pagination Response Structure**
    - **Validates: Requirements 2.1, 2.3**
  - [x] 4.8 Write property test for create-read round trip
    - **Property 3: Create-Read Round Trip**
    - **Validates: Requirements 2.2, 2.4**

- [x] 5. Criar Testes de Integração HTTP para PedidoExample
  - [x] 5.1 Criar tests/integration/interface/test_pedidos_api_http.py
    - Setup com AsyncClient
    - Fixtures para headers de tenant
    - _Requirements: 2.3, 2.4_
  - [x] 5.2 Implementar teste GET /api/v1/examples/pedidos
    - Verificar estrutura de paginação
    - Testar filtro por tenant
    - _Requirements: 2.3_
  - [x] 5.3 Implementar teste POST /api/v1/examples/pedidos
    - Testar criação com dados válidos
    - Verificar resposta 201
    - _Requirements: 2.4_
  - [x] 5.4 Implementar teste GET /api/v1/examples/pedidos/{id}
    - Testar leitura de pedido existente
    - Testar 404 para pedido inexistente
    - _Requirements: 2.3_
  - [x] 5.5 Implementar teste POST /api/v1/examples/pedidos/{id}/items
    - Testar adição de item ao pedido
    - _Requirements: 2.4_
  - [x] 5.6 Implementar teste POST /api/v1/examples/pedidos/{id}/confirm
    - Testar confirmação de pedido
    - _Requirements: 2.4_
  - [x] 5.7 Implementar teste POST /api/v1/examples/pedidos/{id}/cancel
    - Testar cancelamento de pedido
    - _Requirements: 2.4_

- [x] 6. Checkpoint - Verificar testes de integração
  - All 82 tests pass ✅

- [x] 7. Criar Testes de Propriedade para Middleware
  - [x] 7.1 Criar tests/properties/test_interface_middleware_properties.py
    - Setup com estratégias Hypothesis
    - _Requirements: 3.3_
  - [x] 7.2 Write property test for RBAC enforcement
    - **Property 4: RBAC Enforcement**
    - **Validates: Requirements 3.4**
  - [x] 7.3 Write property test for health endpoint
    - **Property 5: Health Endpoint Consistency**
    - **Validates: Requirements 4.4**
  - [x] 7.4 Write property test for tenant context
    - **Property 6: Tenant Context Propagation**
    - **Validates: Requirements 1.3**

- [x] 8. Atualizar Documentação
  - [x] 8.1 Atualizar docs/interface-modules-integration-status.md
    - Documentar middlewares integrados
    - Atualizar status de integração
    - _Requirements: 1.5_
  - [x] 8.2 Criar ADR para decisões de middleware
    - Documentar ordem de middleware
    - Justificar configurações
    - _Requirements: 1.5_

- [x] 9. Final Checkpoint - Verificar todos os testes
  - All tests pass ✅
  - 82 integration tests passed
  - 12 property tests passed

## Summary

All tasks completed successfully:
- ✅ Middlewares integrados em main.py (RequestID, RequestLogger, RequestSizeLimit)
- ✅ Pasta routes/ reorganizada com documentação
- ✅ Testes de integração HTTP para ItemExample (11 tests)
- ✅ Testes de integração HTTP para PedidoExample (13 tests)
- ✅ Testes de propriedade para middleware (12 tests)
- ✅ Documentação atualizada (integration status + ADR)
