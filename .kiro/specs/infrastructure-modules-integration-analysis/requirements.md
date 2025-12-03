# Requirements Document

## Introduction

Este documento analisa a integração dos módulos de infraestrutura (observability, prometheus, ratelimit, rbac, redis) com o workflow do projeto, verificando conexões com o código, bugs potenciais, e possibilidade de testes manuais e automatizados via ItemExample e PedidoExample.

## Glossary

- **Observability**: Módulo de observabilidade que fornece correlation ID, logging estruturado, tracing e métricas
- **Prometheus**: Módulo de métricas Prometheus com decorators e middleware
- **RateLimit**: Módulo de rate limiting genérico com PEP 695
- **RBAC**: Sistema de controle de acesso baseado em roles com generics
- **Redis**: Cliente Redis enterprise com circuit breaker e fallback
- **ItemExample**: Entidade de exemplo para demonstração de CRUD
- **PedidoExample**: Entidade de exemplo para demonstração de pedidos/orders
- **Workflow**: Fluxo de execução da aplicação desde startup até request handling

## Análise de Integração

### Módulo: observability

**Status de Integração: ✅ INTEGRADO**

| Componente | Integração | Arquivo |
|------------|------------|---------|
| LoggingMiddleware | ✅ Usado no main.py | src/main.py:29, 186 |
| CorrelationContext | ✅ Usado no middleware | src/infrastructure/observability/logging_middleware.py |
| TelemetryService | ✅ Usado no health_router | src/interface/v1/health_router.py:25 |

**Conexão com ItemExample/PedidoExample**: Indireta - o middleware de logging captura todas as requisições incluindo as rotas de examples.

### Módulo: prometheus

**Status de Integração: ⚠️ PARCIALMENTE INTEGRADO**

| Componente | Integração | Arquivo |
|------------|------------|---------|
| PrometheusMiddleware | ❌ NÃO usado no main.py | - |
| setup_prometheus | ❌ NÃO chamado | - |
| Decorators (counter, histogram) | ❌ NÃO usados nos use cases | - |

**Problema Identificado**: O módulo prometheus está implementado mas NÃO está integrado no workflow principal. O endpoint `/metrics` não está exposto.

### Módulo: ratelimit

**Status de Integração: ✅ INTEGRADO (via enterprise router)**

| Componente | Integração | Arquivo |
|------------|------------|---------|
| InMemoryRateLimiter | ✅ Usado em dependencies | src/interface/v1/enterprise/dependencies.py:8 |
| RateLimitMiddleware | ❌ NÃO usado globalmente | - |
| Endpoints | ✅ /api/v1/enterprise/ratelimit/* | src/interface/v1/enterprise/ratelimit.py |

**Conexão com ItemExample/PedidoExample**: Nenhuma direta - o rate limiter está disponível apenas nos endpoints enterprise, não protege os endpoints de examples.

### Módulo: rbac

**Status de Integração: ✅ INTEGRADO (via enterprise router)**

| Componente | Integração | Arquivo |
|------------|------------|---------|
| RBAC | ✅ Usado em dependencies | src/interface/v1/enterprise/dependencies.py:9 |
| Permission | ✅ Usado nos endpoints | src/interface/v1/enterprise/rbac.py:10 |
| AuditLogger | ✅ Usado nos endpoints | src/interface/v1/enterprise/rbac.py:13 |
| @requires decorator | ❌ NÃO usado nos examples | - |

**Conexão com ItemExample/PedidoExample**: Nenhuma - os endpoints de examples não usam RBAC.

### Módulo: redis

**Status de Integração: ✅ INTEGRADO**

| Componente | Integração | Arquivo |
|------------|------------|---------|
| RedisClient | ✅ Inicializado no lifespan | src/main.py:39, 97-104 |
| RedisConfig | ✅ Configurado via settings | src/main.py:98-102 |
| CircuitBreaker | ✅ Interno ao client | src/infrastructure/redis/client.py |
| Endpoints | ✅ /api/v1/infrastructure/cache/* | src/interface/v1/infrastructure_router.py |

**Conexão com ItemExample/PedidoExample**: Nenhuma direta - o cache Redis está disponível mas não é usado pelos use cases de examples.

## Requirements

### Requirement 1: Análise de Bugs e Problemas

**User Story:** Como desenvolvedor, quero identificar bugs e problemas de integração nos módulos de infraestrutura, para garantir que o código funcione corretamente.

#### Acceptance Criteria

1. WHEN o módulo prometheus é analisado THEN o sistema SHALL identificar que o PrometheusMiddleware não está registrado no main.py
2. WHEN o módulo prometheus é analisado THEN o sistema SHALL identificar que o endpoint /metrics não está exposto
3. WHEN os módulos ratelimit e rbac são analisados THEN o sistema SHALL identificar que não protegem os endpoints de ItemExample e PedidoExample
4. WHEN o módulo redis é analisado THEN o sistema SHALL identificar que o cache não é utilizado pelos use cases de examples

### Requirement 2: Verificação de Testes Existentes

**User Story:** Como desenvolvedor, quero verificar a cobertura de testes dos módulos de infraestrutura, para garantir qualidade do código.

#### Acceptance Criteria

1. WHEN os testes unitários são verificados THEN o sistema SHALL confirmar existência de testes para redis/circuit_breaker
2. WHEN os testes unitários são verificados THEN o sistema SHALL confirmar existência de testes para prometheus/metrics
3. WHEN os testes unitários são verificados THEN o sistema SHALL confirmar existência de testes para ratelimit/limiter
4. WHEN os testes unitários são verificados THEN o sistema SHALL confirmar existência de testes para rbac/rbac
5. WHEN os testes de integração são verificados THEN o sistema SHALL identificar ausência de testes de integração para os módulos de infraestrutura

### Requirement 3: Possibilidade de Testes Manuais via Docker

**User Story:** Como desenvolvedor, quero testar manualmente os módulos de infraestrutura via Docker, para validar o funcionamento em ambiente real.

#### Acceptance Criteria

1. WHEN o docker-compose.infra.yml é analisado THEN o sistema SHALL confirmar disponibilidade de Redis (porta 6379)
2. WHEN o docker-compose.infra.yml é analisado THEN o sistema SHALL confirmar disponibilidade de Prometheus (porta 9090)
3. WHEN o docker-compose.infra.yml é analisado THEN o sistema SHALL confirmar disponibilidade de Grafana (porta 3000)
4. WHEN o docker-compose.dev.yml é analisado THEN o sistema SHALL confirmar configuração de hot-reload para desenvolvimento
5. IF os serviços de infraestrutura estiverem rodando THEN o sistema SHALL permitir testes manuais via endpoints /api/v1/infrastructure/* e /api/v1/enterprise/*

### Requirement 4: Conexão com ItemExample e PedidoExample

**User Story:** Como desenvolvedor, quero entender como os módulos de infraestrutura podem ser conectados aos examples, para demonstrar uso real.

#### Acceptance Criteria

1. WHEN o ItemExampleUseCase é analisado THEN o sistema SHALL identificar que não utiliza cache Redis
2. WHEN o PedidoExampleUseCase é analisado THEN o sistema SHALL identificar que não utiliza rate limiting
3. WHEN os endpoints de examples são analisados THEN o sistema SHALL identificar que não utilizam RBAC
4. WHEN os use cases são analisados THEN o sistema SHALL identificar que não utilizam métricas Prometheus

## Resumo de Problemas Encontrados

### Bugs/Problemas Críticos

1. **Prometheus não integrado**: O módulo está implementado mas não está sendo usado no main.py
2. **Endpoint /metrics ausente**: Não há exposição de métricas Prometheus

### Problemas de Integração

1. **Redis não usado nos examples**: O cache está disponível mas ItemExample/PedidoExample não o utilizam
2. **RateLimit não protege examples**: Os endpoints de examples não têm rate limiting
3. **RBAC não protege examples**: Os endpoints de examples não têm controle de acesso
4. **Métricas não coletadas nos use cases**: Não há instrumentação de métricas nos use cases

### Testes Ausentes

1. **Testes de integração**: Não há testes de integração para redis, prometheus, ratelimit, rbac com os examples
2. **Testes E2E**: Não há testes end-to-end que validem o fluxo completo com infraestrutura

## Comandos para Testes Manuais

```bash
# Subir infraestrutura
cd deployments/docker
docker compose -f docker-compose.base.yml -f docker-compose.infra.yml up -d

# Subir API em desenvolvimento
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d

# Testar Redis via API
curl -X POST http://localhost:8000/api/v1/infrastructure/cache \
  -H "Content-Type: application/json" \
  -d '{"key": "test:1", "value": {"name": "Test"}, "ttl": 3600}'

# Testar Rate Limit
curl -X POST http://localhost:8000/api/v1/enterprise/ratelimit/check \
  -H "Content-Type: application/json" \
  -d '{"client_id": "user-123"}'

# Testar RBAC
curl -X POST http://localhost:8000/api/v1/enterprise/rbac/check \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-1", "user_roles": ["viewer"], "resource": "document", "action": "read"}'

# Testar ItemExample (sem infraestrutura)
curl http://localhost:8000/api/v1/examples/items
```
