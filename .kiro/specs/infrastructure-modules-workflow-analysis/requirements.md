# Requirements Document

## Introduction

Análise detalhada dos módulos de infraestrutura: resilience, scylladb, security, storage e tasks. Este documento avalia a integração com o workflow do projeto, bugs potenciais, conexões com o código, e possibilidade de testes via ItemExample/PedidoExample e testes manuais via Docker.

## Glossary

- **Resilience**: Módulo com padrões de resiliência (CircuitBreaker, Retry, Timeout, Bulkhead, Fallback)
- **ScyllaDB**: Cliente e repositório genérico para banco NoSQL ScyllaDB
- **Security**: Módulo de segurança com RBAC, field encryption, rate limiting, audit
- **Storage**: Módulo de upload de arquivos com validação e streaming
- **Tasks**: Sistema de filas de tarefas com RabbitMQ e in-memory
- **ItemExample**: Entidade de exemplo para demonstração de CRUD
- **PedidoExample**: Entidade de exemplo para demonstração de pedidos

## Análise de Integração por Módulo

### 1. Módulo: resilience (src/infrastructure/resilience)

| Componente | Status | Uso no Workflow | Localização |
|------------|--------|-----------------|-------------|
| CircuitBreaker | ✅ Exportado | ✅ Usado em production middleware | src/interface/middleware/production.py:36 |
| Retry | ✅ Exportado | ❌ NÃO usado diretamente | - |
| Timeout | ✅ Exportado | ❌ NÃO usado diretamente | - |
| Bulkhead | ✅ Exportado | ❌ NÃO usado diretamente | - |
| Fallback | ✅ Exportado | ❌ NÃO usado diretamente | - |

**Conexão com ItemExample/PedidoExample**: Indireta - o CircuitBreaker está configurado no middleware de produção que protege todas as rotas.

**Bugs/Problemas Identificados**:
1. ⚠️ Testes de propriedade estão SKIPPED: `test_circuit_breaker_properties.py` e `test_bulkhead_properties.py` indicam que módulos `infrastructure.resilience.circuit_breaker` e `infrastructure.resilience.bulkhead` não estão implementados como arquivos separados
2. ⚠️ O módulo patterns.py implementa tudo, mas os testes esperam arquivos separados

**Testabilidade**:
- ✅ Testes de propriedade existem mas estão skipped
- ✅ Pode ser testado manualmente via middleware de produção

### 2. Módulo: scylladb (src/infrastructure/scylladb)

| Componente | Status | Uso no Workflow | Localização |
|------------|--------|-----------------|-------------|
| ScyllaDBClient | ✅ Implementado | ❌ NÃO usado no main.py | - |
| ScyllaDBConfig | ✅ Implementado | ✅ Configurado em settings | src/core/config/observability.py:84 |
| ScyllaDBEntity | ✅ Implementado | ❌ NÃO usado | - |
| ScyllaDBRepository | ✅ Implementado | ❌ NÃO usado | - |

**Conexão com ItemExample/PedidoExample**: NENHUMA - ItemExample usa SQLModel/PostgreSQL, não ScyllaDB.

**Bugs/Problemas Identificados**:
1. ❌ Módulo ÓRFÃO - configuração existe mas não há inicialização no main.py
2. ❌ Não há inicialização no lifespan do main.py (diferente de Redis, MinIO, Kafka)
3. ✅ Configuração existe: OBSERVABILITY__SCYLLADB_ENABLED, SCYLLADB_HOSTS, etc.
4. ⚠️ Docker-compose.infra.yml tem ScyllaDB mas aplicação não o inicializa

**Testabilidade**:
- ✅ Testes unitários existem: test_config.py, test_entity.py, test_repository.py
- ❌ NÃO pode ser testado via ItemExample/PedidoExample
- ⚠️ Teste manual requer criar entidade específica para ScyllaDB

### 3. Módulo: security (src/infrastructure/security)

| Componente | Status | Uso no Workflow | Localização |
|------------|--------|-----------------|-------------|
| RBAC | ✅ Implementado | ✅ Usado em enterprise_examples_router | src/interface/v1/enterprise_examples_router.py |
| FieldEncryption | ✅ Implementado | ❌ NÃO usado nos examples | - |
| PasswordHashers | ✅ Re-export | ✅ Usado em auth | src/infrastructure/auth/password_policy.py |
| RateLimit | ✅ Implementado | ✅ Usado no main.py | src/main.py:_configure_rate_limiting |
| AuditLogger | ✅ Implementado | ✅ Usado em production middleware | src/interface/middleware/production.py |

**Conexão com ItemExample/PedidoExample**: 
- ⚠️ RBAC disponível mas NÃO protege endpoints de examples
- ⚠️ RateLimit configurado para /api/v1/examples/* mas sem autenticação

**Bugs/Problemas Identificados**:
1. ⚠️ Endpoints de ItemExample/PedidoExample não usam RBAC
2. ⚠️ FieldEncryption não é usado em nenhum campo sensível
3. ✅ RateLimit está configurado corretamente para examples

**Testabilidade**:
- ✅ Testes de propriedade extensivos existem
- ✅ Pode ser testado manualmente via /api/v1/enterprise/rbac/*
- ⚠️ Para testar com ItemExample, precisa adicionar decorators RBAC

### 4. Módulo: storage (src/infrastructure/storage)

| Componente | Status | Uso no Workflow | Localização |
|------------|--------|-----------------|-------------|
| FileUploadHandler | ✅ Implementado | ❌ NÃO usado | - |
| FileValidator | ✅ Implementado | ❌ NÃO usado | - |
| FileStorage | ✅ Protocol | ❌ NÃO implementado | - |
| FileInfo | ✅ Implementado | ❌ NÃO usado | - |

**Conexão com ItemExample/PedidoExample**: NENHUMA - não há upload de arquivos nos examples.

**Bugs/Problemas Identificados**:
1. ❌ Módulo ÓRFÃO - não está conectado ao workflow
2. ❌ FileStorage é apenas Protocol, não há implementação concreta
3. ❌ MinIO está configurado no main.py mas não usa este módulo
4. ⚠️ Não há endpoint para upload de arquivos

**Testabilidade**:
- ⚠️ Teste de propriedade test_archival_properties.py está SKIPPED
- ❌ NÃO pode ser testado via ItemExample/PedidoExample
- ❌ NÃO pode ser testado manualmente (sem endpoints)

### 5. Módulo: tasks (src/infrastructure/tasks)

| Componente | Status | Uso no Workflow | Localização |
|------------|--------|-----------------|-------------|
| InMemoryTaskQueue | ✅ Implementado | ❌ NÃO usado | - |
| RabbitMQTaskQueue | ✅ Implementado | ✅ Usado em enterprise | src/interface/v1/enterprise/dependencies.py:98 |
| RabbitMQWorker | ✅ Implementado | ⚠️ Disponível mas não iniciado | - |
| RabbitMQRpcClient | ✅ Implementado | ⚠️ Disponível mas não usado | - |
| Task | ✅ Implementado | ✅ Usado em enterprise | - |
| RetryPolicy | ✅ Implementado | ✅ Usado internamente | - |

**Conexão com ItemExample/PedidoExample**: NENHUMA - tasks são usados apenas em enterprise examples (email tasks).

**Bugs/Problemas Identificados**:
1. ⚠️ RabbitMQ não é inicializado no main.py lifespan (diferente de Kafka)
2. ⚠️ Conexão é lazy (criada sob demanda em get_task_queue)
3. ⚠️ Apenas enterprise_examples_router usa tasks para EmailTaskPayload
4. ✅ Implementação está completa e funcional com fallback in-memory

**Testabilidade**:
- ✅ Testes unitários existem: test_rabbitmq.py
- ✅ Testes de propriedade existem: test_background_tasks_properties.py
- ⚠️ Teste manual requer RabbitMQ rodando via Docker

## Requirements

### Requirement 1: Análise de Código Órfão

**User Story:** Como desenvolvedor, quero identificar código não conectado ao workflow, para decidir se deve ser removido ou integrado.

#### Acceptance Criteria

1. WHEN o módulo scylladb é analisado THEN o sistema SHALL identificar que não está conectado ao main.py
2. WHEN o módulo storage é analisado THEN o sistema SHALL identificar que FileStorage não tem implementação concreta
3. WHEN o módulo resilience é analisado THEN o sistema SHALL identificar que apenas CircuitBreaker está em uso ativo

### Requirement 2: Análise de Testabilidade

**User Story:** Como desenvolvedor, quero saber quais módulos podem ser testados via ItemExample/PedidoExample.

#### Acceptance Criteria

1. WHEN os módulos são analisados THEN o sistema SHALL identificar que apenas security/ratelimit afeta ItemExample/PedidoExample
2. WHEN os testes são analisados THEN o sistema SHALL identificar testes skipped por módulos não implementados
3. WHEN a testabilidade manual é avaliada THEN o sistema SHALL listar endpoints disponíveis

### Requirement 3: Análise de Testes Manuais via Docker

**User Story:** Como desenvolvedor, quero saber como testar manualmente os módulos via Docker.

#### Acceptance Criteria

1. WHEN docker-compose.infra.yml é analisado THEN o sistema SHALL identificar serviços disponíveis
2. WHEN a API é iniciada THEN o sistema SHALL permitir testes via endpoints /api/v1/*
3. IF ScyllaDB estiver rodando THEN o sistema SHALL permitir conexão na porta 9042
4. IF RabbitMQ estiver rodando THEN o sistema SHALL permitir conexão na porta 5672

## Resumo de Status

| Módulo | Conectado ao Workflow | Testável via Examples | Testável Manual | Bugs Críticos |
|--------|----------------------|----------------------|-----------------|---------------|
| resilience | ✅ Parcial | ⚠️ Indireto | ✅ Sim | ⚠️ Testes skipped |
| scylladb | ❌ Não | ❌ Não | ⚠️ Requer setup | ❌ Órfão |
| security | ✅ Sim | ⚠️ Parcial | ✅ Sim | ⚠️ RBAC não protege examples |
| storage | ❌ Não | ❌ Não | ❌ Não | ❌ Órfão, sem implementação |
| tasks | ✅ Parcial | ❌ Não | ✅ Sim | ⚠️ RabbitMQ não inicializado |

## Comandos para Teste Manual

```bash
# Subir infraestrutura
cd deployments/docker
docker compose -f docker-compose.base.yml -f docker-compose.infra.yml up -d

# Subir API em desenvolvimento
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d

# Ou localmente
cd src
uvicorn main:app --reload

# Testar ItemExample
curl http://localhost:8000/api/v1/examples/items
curl -X POST http://localhost:8000/api/v1/examples/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Item", "description": "Test", "price": 10.0, "quantity": 5}'

# Testar PedidoExample
curl http://localhost:8000/api/v1/examples/pedidos

# Testar Rate Limiting (deve bloquear após 100 requests/min)
for i in {1..110}; do curl -s http://localhost:8000/api/v1/examples/items; done

# Testar RBAC (enterprise)
curl -X POST http://localhost:8000/api/v1/enterprise/rbac/check \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-1", "user_roles": ["admin"], "resource": "item", "action": "read"}'
```
