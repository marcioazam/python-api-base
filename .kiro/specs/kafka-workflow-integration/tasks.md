# Implementation Plan

## Kafka Workflow Integration

Este plano implementa a integração do módulo Kafka ao workflow principal da aplicação.

---

- [x] 1. Adicionar inicialização do Kafka no lifespan
  - [x] 1.1 Modificar src/main.py para inicializar KafkaProducer quando kafka_enabled=true
    - Importar KafkaProducer e KafkaConfig de infrastructure.kafka
    - Criar KafkaConfig a partir de ObservabilitySettings
    - Inicializar producer com try/except para graceful degradation
    - Armazenar em app.state.kafka_producer
    - _Requirements: 1.1, 1.2, 1.3, 1.5_
  - [x] 1.2 Adicionar cleanup do Kafka no shutdown do lifespan
    - Chamar producer.stop() se producer existir
    - _Requirements: 1.4_
  - [x] 1.3 Write property test for Kafka initialization
    - **Property 1: Kafka Initialization Respects Configuration**
    - **Property 2: Graceful Degradation on Connection Failure**
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 2. Criar endpoints de teste Kafka no infrastructure_router
  - [x] 2.1 Adicionar DTOs para Kafka (KafkaPublishRequest, KafkaPublishResponse, KafkaStatusResponse)
    - Criar modelos Pydantic para request/response
    - _Requirements: 2.1, 2.2_
  - [x] 2.2 Implementar dependency get_kafka() para obter producer do app.state
    - Retornar HTTPException 503 se Kafka não configurado
    - _Requirements: 2.3_
  - [x] 2.3 Implementar endpoint POST /kafka/publish
    - Aceitar topic, key, payload, headers
    - Retornar metadata (topic, partition, offset, timestamp)
    - _Requirements: 2.1, 2.4_
  - [x] 2.4 Implementar endpoint GET /kafka/status
    - Retornar enabled, connected, client_id, bootstrap_servers
    - _Requirements: 2.2_
  - [x] 2.5 Write unit tests for Kafka endpoints
    - Testar publish com mock producer
    - Testar status endpoint
    - Testar 503 quando Kafka desabilitado
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Checkpoint - Verificar endpoints funcionando
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Criar módulo de Event Publisher
  - [x] 4.1 Criar src/infrastructure/kafka/event_publisher.py
    - Definir DomainEvent dataclass genérico
    - Definir EventPublisher ABC
    - Implementar KafkaEventPublisher
    - Implementar NoOpEventPublisher para quando Kafka desabilitado
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 4.2 Criar eventos de domínio para ItemExample
    - ItemCreatedEvent, ItemUpdatedEvent, ItemDeletedEvent
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 4.3 Atualizar __init__.py do módulo kafka para exportar novos componentes
    - Exportar EventPublisher, KafkaEventPublisher, NoOpEventPublisher
    - Exportar eventos de domínio
    - _Requirements: 3.1_
  - [x] 4.4 Write property test for event publishing
    - **Property 5: Domain Event Publishing for CRUD Operations**
    - **Property 6: Silent Skip When Kafka Disabled**
    - **Property 7: Non-Blocking Event Publishing Failures**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

- [x] 5. Integrar Event Publisher ao ItemExampleUseCase
  - [x] 5.1 Modificar ItemExampleUseCase para aceitar EventPublisher opcional
    - Adicionar parâmetro event_publisher no construtor
    - _Requirements: 3.1_
  - [x] 5.2 Publicar ItemCreatedEvent no método create
    - Criar evento após persistência bem-sucedida
    - Usar try/except para não falhar operação principal
    - _Requirements: 3.1, 3.5_
  - [x] 5.3 Publicar ItemUpdatedEvent no método update
    - Incluir changes no payload do evento
    - _Requirements: 3.2, 3.5_
  - [x] 5.4 Publicar ItemDeletedEvent no método delete
    - _Requirements: 3.3, 3.5_
  - [x] 5.5 Atualizar router para injetar EventPublisher no use case
    - Criar dependency get_event_publisher()
    - Usar KafkaEventPublisher se Kafka habilitado, NoOpEventPublisher caso contrário
    - _Requirements: 3.4_
  - [x] 5.6 Write integration tests for event publishing
    - Testar que eventos são publicados em operações CRUD
    - Testar que falha de publicação não afeta operação principal
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [x] 6. Checkpoint - Verificar integração completa
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Adicionar property test para serialização de mensagens
  - [x] 7.1 Write property test for message round-trip
    - **Property 4: Message Serialization Round-Trip**
    - Testar com payloads e headers aleatórios
    - Verificar que deserialização produz mensagem equivalente
    - **Validates: Requirements 4.1, 4.2**

- [x] 8. Atualizar documentação
  - [x] 8.1 Atualizar .env.example com variáveis Kafka
    - Adicionar OBSERVABILITY__KAFKA_ENABLED=false
    - Adicionar exemplo de configuração para Docker local
    - _Requirements: 5.1, 5.2_
  - [x] 8.2 Atualizar docs/configuration.md com seção Kafka
    - Documentar todas as variáveis de ambiente
    - Incluir exemplo de configuração SASL
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 9. Final Checkpoint - Verificar todos os testes passando
  - Ensure all tests pass, ask the user if questions arise.

