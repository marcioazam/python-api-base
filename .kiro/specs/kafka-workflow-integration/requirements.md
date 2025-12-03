# Requirements Document

## Introduction

Este documento especifica os requisitos para integrar o módulo Kafka existente (`src/infrastructure/kafka`) ao workflow principal da aplicação Python API Base. O objetivo é permitir que desenvolvedores testem a funcionalidade Kafka via API e que eventos de domínio sejam publicados automaticamente quando entidades são criadas/atualizadas/deletadas.

## Glossary

- **KafkaProducer**: Produtor genérico assíncrono para envio de mensagens ao Kafka
- **KafkaConsumer**: Consumidor genérico assíncrono para recebimento de mensagens do Kafka
- **KafkaConfig**: Configuração do cliente Kafka (bootstrap servers, security, etc.)
- **KafkaMessage**: Wrapper type-safe para mensagens Kafka com payload genérico
- **Domain Event**: Evento que representa uma mudança de estado em uma entidade de domínio
- **ItemExample**: Entidade de exemplo para demonstração de CRUD
- **Lifespan**: Contexto de ciclo de vida da aplicação FastAPI

---

## Requirements

### Requirement 1: Inicialização do Kafka no Startup

**User Story:** As a developer, I want Kafka to be initialized on application startup, so that I can publish messages without manual setup.

#### Acceptance Criteria

1. WHEN KAFKA_ENABLED is true THEN the System SHALL initialize KafkaProducer during application lifespan startup
2. WHEN KAFKA_ENABLED is false THEN the System SHALL skip Kafka initialization and log informational message
3. WHEN Kafka connection fails during startup THEN the System SHALL log error and continue startup without blocking
4. WHEN the application shuts down THEN the System SHALL gracefully close Kafka producer connection
5. WHEN Kafka producer is initialized THEN the System SHALL store reference in app.state.kafka_producer

---

### Requirement 2: Endpoints de Teste Kafka

**User Story:** As a developer, I want API endpoints to test Kafka functionality, so that I can verify the integration works correctly.

#### Acceptance Criteria

1. WHEN a developer sends POST to /api/v1/infrastructure/kafka/publish THEN the System SHALL publish test message to configured topic
2. WHEN a developer sends GET to /api/v1/infrastructure/kafka/status THEN the System SHALL return producer connection status
3. WHEN Kafka is not enabled THEN the endpoints SHALL return 503 Service Unavailable with descriptive message
4. WHEN message is published successfully THEN the endpoint SHALL return message metadata (topic, partition, offset)

---

### Requirement 3: Publicação de Eventos de Domínio

**User Story:** As a developer, I want domain events to be published to Kafka automatically, so that I can build event-driven architectures.

#### Acceptance Criteria

1. WHEN ItemExample entity is created THEN the System SHALL publish ItemCreated event to items-events topic
2. WHEN ItemExample entity is updated THEN the System SHALL publish ItemUpdated event to items-events topic
3. WHEN ItemExample entity is deleted THEN the System SHALL publish ItemDeleted event to items-events topic
4. WHEN Kafka is disabled THEN the System SHALL skip event publishing without error
5. WHEN event publishing fails THEN the System SHALL log error but not fail the main operation

---

### Requirement 4: Serialização de Mensagens

**User Story:** As a developer, I want messages to be serialized correctly, so that consumers can deserialize them reliably.

#### Acceptance Criteria

1. WHEN KafkaMessage is serialized THEN deserializing the bytes SHALL produce equivalent message payload
2. WHEN message headers are set THEN serialization SHALL preserve all header key-value pairs
3. WHEN message key is provided THEN the System SHALL use it for partition routing
4. WHEN payload is Pydantic model THEN the System SHALL serialize using model_dump_json

---

### Requirement 5: Configuração via Environment Variables

**User Story:** As a DevOps engineer, I want to configure Kafka via environment variables, so that I can deploy to different environments easily.

#### Acceptance Criteria

1. WHEN OBSERVABILITY__KAFKA_ENABLED is set THEN the System SHALL use this value to enable/disable Kafka
2. WHEN OBSERVABILITY__KAFKA_BOOTSTRAP_SERVERS is set THEN the System SHALL connect to specified brokers
3. WHEN OBSERVABILITY__KAFKA_SECURITY_PROTOCOL is SASL_SSL THEN the System SHALL use SASL authentication
4. WHEN credentials are missing for SASL THEN the System SHALL raise configuration validation error

---

### Requirement 6: Integração com Docker Compose

**User Story:** As a developer, I want to test Kafka locally with Docker, so that I can develop without external dependencies.

#### Acceptance Criteria

1. WHEN docker-compose.infra.yml is running THEN the Kafka service SHALL be available on localhost:29092
2. WHEN .env.example is copied THEN the default Kafka configuration SHALL work with local Docker setup
3. WHEN Kafka container is healthy THEN the API SHALL successfully connect and publish messages
