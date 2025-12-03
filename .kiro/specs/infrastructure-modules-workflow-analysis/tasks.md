# Implementation Plan

- [x] 1. Corrigir módulo Resilience (arquivos separados)
  - [x] 1.1 Criar infrastructure/resilience/circuit_breaker.py
    - Re-exportar CircuitBreaker, CircuitBreakerConfig, CircuitState de patterns.py
    - _Requirements: 1.3_
  - [x] 1.2 Criar infrastructure/resilience/bulkhead.py
    - Re-exportar Bulkhead, BulkheadConfig de patterns.py
    - _Requirements: 1.3_
  - [x] 1.3 Criar infrastructure/resilience/retry.py (se não existir)
    - Re-exportar Retry, RetryConfig, ExponentialBackoff de patterns.py
    - _Requirements: 1.3_
  - [x] 1.4 Criar infrastructure/resilience/timeout.py
    - Re-exportar Timeout, TimeoutConfig de patterns.py
    - _Requirements: 1.3_
  - [x] 1.5 Criar infrastructure/resilience/fallback.py
    - Re-exportar Fallback de patterns.py
    - _Requirements: 1.3_
  - [x] 1.6 Atualizar testes de propriedade do resilience
    - Remover pytest.skip dos testes test_circuit_breaker_properties.py e test_bulkhead_properties.py
    - **Property 3: Resilience Module Exports**
    - **Validates: Requirements 1.3**

- [x] 2. Integrar ScyllaDB ao workflow
  - [x] 2.1 Adicionar configuração RabbitMQ em observability.py
    - Adicionar rabbitmq_enabled, rabbitmq_host, rabbitmq_port, rabbitmq_username, rabbitmq_password
    - _Requirements: 3.4_
  - [x] 2.2 Adicionar inicialização ScyllaDB no main.py lifespan
    - Verificar scylladb_enabled antes de inicializar
    - Criar ScyllaDBConfig a partir de settings
    - Conectar ScyllaDBClient e armazenar em app.state.scylladb
    - Adicionar cleanup no shutdown
    - _Requirements: 1.1_
  - [x] 2.3 Escrever teste de propriedade para inicialização ScyllaDB
    - **Property 1: ScyllaDB Initialization Consistency**
    - **Validates: Requirements 1.1**

- [x] 3. Implementar MinIOStorageProvider
  - [x] 3.1 Criar infrastructure/storage/minio_provider.py
    - Implementar classe MinIOStorageProvider que implementa FileStorage protocol
    - Métodos: upload, download, delete, exists, generate_signed_url
    - Usar MinIOClient existente internamente
    - _Requirements: 1.2_
  - [x] 3.2 Criar infrastructure/storage/memory_provider.py
    - Implementar InMemoryStorageProvider para testes
    - _Requirements: 1.2_
  - [x] 3.3 Atualizar infrastructure/storage/__init__.py
    - Exportar MinIOStorageProvider e InMemoryStorageProvider
    - _Requirements: 1.2_
  - [x] 3.4 Escrever teste de propriedade para Storage Provider
    - **Property 2: Storage Provider Implementation**
    - **Validates: Requirements 1.2**

- [x] 4. Checkpoint - Verificar testes passando
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Integrar RabbitMQ ao workflow
  - [x] 5.1 Adicionar inicialização RabbitMQ no main.py lifespan
    - Verificar rabbitmq_enabled antes de inicializar
    - Criar RabbitMQConfig a partir de settings
    - Conectar e armazenar em app.state.rabbitmq
    - Adicionar cleanup no shutdown
    - _Requirements: 3.4_
  - [x] 5.2 Escrever teste de propriedade para inicialização RabbitMQ
    - **Property 4: RabbitMQ Initialization Consistency**
    - **Validates: Requirements 3.4**

- [x] 6. Adicionar RBAC aos endpoints de Examples
  - [x] 6.1 Criar dependency get_current_user_optional em examples/router.py
    - Retornar usuário autenticado ou None para requests sem auth
    - _Requirements: 2.1_
  - [x] 6.2 Adicionar RBAC aos endpoints POST/PUT/DELETE de items
    - Usar @require_permission decorator
    - Manter GET público para demonstração
    - _Requirements: 2.1_
  - [x] 6.3 Adicionar RBAC aos endpoints POST de pedidos
    - Usar @require_permission decorator
    - _Requirements: 2.1_
  - [x] 6.4 Escrever teste de propriedade para RBAC em Examples
    - **Property 5: RBAC Protection on Examples**
    - **Validates: Requirements 2.1**

- [x] 7. Atualizar documentação
  - [x] 7.1 Atualizar docs/configuration.md
    - Documentar novas variáveis de ambiente para RabbitMQ
    - _Requirements: 3.4_
  - [x] 7.2 Atualizar docs/modules.md
    - Documentar MinIOStorageProvider
    - Documentar arquivos separados do resilience
    - _Requirements: 1.2, 1.3_

- [x] 8. Final Checkpoint - Verificar todos os testes passando
  - Ensure all tests pass, ask the user if questions arise.

## Resumo da Implementação

### Arquivos Criados
- `src/infrastructure/resilience/circuit_breaker.py` - CircuitBreaker com implementação completa
- `src/infrastructure/resilience/bulkhead.py` - Bulkhead com BulkheadRegistry, BulkheadStats
- `src/infrastructure/resilience/retry_pattern.py` - Re-exports de Retry, RetryConfig
- `src/infrastructure/resilience/timeout.py` - Re-exports de Timeout, TimeoutConfig
- `src/infrastructure/resilience/fallback.py` - Re-exports de Fallback
- `src/infrastructure/storage/minio_provider.py` - MinIOStorageProvider
- `src/infrastructure/storage/memory_provider.py` - InMemoryStorageProvider
- `tests/properties/test_infrastructure_workflow_properties.py` - Testes de propriedade

### Arquivos Modificados
- `src/main.py` - Adicionada inicialização de ScyllaDB e RabbitMQ
- `src/interface/v1/examples/router.py` - Adicionado RBAC aos endpoints
- `src/infrastructure/storage/__init__.py` - Exporta novos providers
- `tests/properties/test_bulkhead_properties.py` - Removido pytest.skip
- `tests/properties/test_circuit_breaker_properties.py` - Removido pytest.skip
- `docs/modules.md` - Documentação atualizada
