# Requirements Document

## Introduction

Este documento especifica os requisitos para implementação de uma infraestrutura enterprise-grade de mensageria, bancos de dados, observabilidade e segurança para a API Python. O sistema deve suportar comunicação assíncrona entre microservices via Kafka/Redpanda e RabbitMQ/NATS, persistência em PostgreSQL, ScyllaDB/MongoDB e Redis, além de observabilidade completa com OpenTelemetry, Prometheus e logging estruturado.

**Foco Principal: Generics<T> (PEP 695)**
A implementação deve usar extensivamente os novos type parameters do Python 3.12+ para criar abstrações reutilizáveis e type-safe. Cada componente de infraestrutura deve expor interfaces genéricas que garantam segurança de tipos em tempo de compilação (mypy/pyright) e máxima reutilização de código.

## Glossary

- **Generic_Publisher[TMessage]**: Publisher genérico parametrizado pelo tipo de mensagem, garantindo type-safety na serialização
- **Generic_Consumer[TMessage, TResult]**: Consumer genérico com tipo de mensagem e resultado, permitindo handlers tipados
- **Generic_Repository[TEntity, TId]**: Repositório genérico parametrizado por entidade e tipo de ID para operações CRUD
- **Generic_Cache[TKey, TValue]**: Cache genérico com tipos de chave e valor para armazenamento tipado
- **Generic_EventHandler[TEvent]**: Handler de eventos genérico para processamento tipado de eventos de domínio
- **Generic_Serializer[T]**: Serializador genérico que preserva informação de tipo para round-trip
- **Generic_Validator[T]**: Validador genérico baseado em Pydantic para validação tipada
- **Generic_Client[TRequest, TResponse]**: Cliente HTTP genérico com request/response tipados
- **Generic_Middleware[TContext]**: Middleware genérico com contexto tipado para pipeline de processamento
- **Protocol[T]**: Interface estrutural para duck typing com suporte a generics
- **TypeVar**: Variável de tipo para parametrização de classes e funções
- **Bounded_TypeVar**: TypeVar com constraints (upper bounds) para restringir tipos aceitos
- **Covariant/Contravariant**: Variância de tipos para herança correta em generics
- **Event_Bus**: Barramento de eventos Kafka/Redpanda
- **Task_Queue**: Fila de tarefas RabbitMQ/NATS
- **Cache_Layer**: Camada de cache Redis
- **Tracer**: Componente OpenTelemetry
- **Metrics_Collector**: Coletor Prometheus
- **Structured_Logger**: Logger structlog/Loguru
- **Auth_Provider**: Provedor Keycloak/Auth0/Firebase
- **RBAC_System**: Sistema de controle de acesso baseado em roles
- **Circuit_Breaker**: Padrão de resiliência

## Requirements

### Requirement 1: Generic Message Publishing System (Kafka/Redpanda)

**User Story:** As a developer, I want a type-safe generic publisher for Kafka/Redpanda, so that I can publish strongly-typed events with compile-time validation.

#### Acceptance Criteria

1. WHEN defining Generic_Publisher[TMessage] THEN the type parameter TMessage SHALL be constrained to classes with Pydantic BaseModel or dataclass decorator
2. WHEN publishing a message THEN Generic_Publisher[TMessage].publish(message: TMessage) SHALL validate the message type at compile time via mypy/pyright
3. WHEN serializing messages THEN Generic_Serializer[TMessage].serialize(message: TMessage) SHALL produce bytes that deserialize to equivalent TMessage instance (round-trip property)
4. WHEN deserializing messages THEN Generic_Serializer[TMessage].deserialize(data: bytes) SHALL return TMessage or raise typed DeserializationError[TMessage]
5. WHEN using transactional producer THEN Generic_Publisher[TMessage].publish_transactional(messages: list[TMessage]) SHALL ensure exactly-once delivery
6. WHEN the broker is unavailable THEN Generic_Publisher[TMessage] SHALL buffer messages in Generic_Buffer[TMessage] and retry with Circuit_Breaker
7. WHEN configuring topics THEN Generic_Publisher[TMessage].configure(topic: str, partitioner: Callable[[TMessage], int]) SHALL accept typed partitioner function
8. WHEN using schema registry THEN Generic_Publisher[TMessage] SHALL register and validate Avro schema derived from TMessage type

### Requirement 2: Generic Message Consumption System (Kafka/Redpanda)

**User Story:** As a developer, I want a type-safe generic consumer for Kafka/Redpanda, so that I can process strongly-typed events with automatic deserialization.

#### Acceptance Criteria

1. WHEN defining Generic_Consumer[TMessage, TResult] THEN the handler signature SHALL be Callable[[TMessage], Awaitable[TResult]]
2. WHEN consuming messages THEN Generic_Consumer[TMessage, TResult].consume(handler: Callable[[TMessage], Awaitable[TResult]]) SHALL deserialize to TMessage before calling handler
3. WHEN handler returns TResult THEN Generic_Consumer[TMessage, TResult] SHALL acknowledge message and optionally publish TResult to output topic
4. WHEN handler raises exception THEN Generic_Consumer[TMessage, TResult] SHALL retry with typed RetryPolicy[TMessage] and send to Generic_DeadLetterQueue[TMessage]
5. WHEN using consumer groups THEN Generic_Consumer[TMessage, TResult].join_group(group_id: str) SHALL coordinate partition assignment
6. WHEN committing offsets THEN Generic_Consumer[TMessage, TResult] SHALL support both auto-commit and manual commit with typed CommitResult
7. WHEN filtering messages THEN Generic_Consumer[TMessage, TResult].filter(predicate: Callable[[TMessage], bool]) SHALL apply typed predicate before processing

### Requirement 3: Generic Task Queue System (RabbitMQ/NATS)

**User Story:** As a developer, I want a type-safe generic task queue, so that I can enqueue and process background tasks with compile-time type validation.

#### Acceptance Criteria

1. WHEN defining Generic_TaskQueue[TTask, TResult] THEN TTask SHALL be constrained to Pydantic BaseModel with task metadata
2. WHEN enqueueing tasks THEN Generic_TaskQueue[TTask, TResult].enqueue(task: TTask) SHALL return typed TaskHandle[TTask, TResult] with task ID
3. WHEN processing tasks THEN Generic_Worker[TTask, TResult].process(handler: Callable[[TTask], Awaitable[TResult]]) SHALL deserialize TTask and call typed handler
4. WHEN task completes THEN TaskHandle[TTask, TResult].result() SHALL return TResult or raise typed TaskError[TTask]
5. WHEN using RPC pattern THEN Generic_RpcClient[TRequest, TResponse].call(request: TRequest) SHALL return Awaitable[TResponse] with correlation
6. WHEN serializing tasks THEN Generic_Serializer[TTask].serialize(task: TTask) SHALL produce JSON that deserializes to equivalent TTask (round-trip property)
7. WHEN scheduling tasks THEN Generic_TaskQueue[TTask, TResult].schedule(task: TTask, delay: timedelta) SHALL support delayed execution
8. WHEN prioritizing tasks THEN Generic_TaskQueue[TTask, TResult].enqueue(task: TTask, priority: int) SHALL support priority queues

### Requirement 4: Generic Cache System (Redis)

**User Story:** As a developer, I want a type-safe generic cache, so that I can store and retrieve strongly-typed values with automatic serialization.

#### Acceptance Criteria

1. WHEN defining Generic_Cache[TKey, TValue] THEN TKey SHALL be constrained to Hashable and TValue to Pydantic BaseModel
2. WHEN caching values THEN Generic_Cache[TKey, TValue].set(key: TKey, value: TValue, ttl: timedelta) SHALL serialize TValue and store with TTL
3. WHEN retrieving values THEN Generic_Cache[TKey, TValue].get(key: TKey) SHALL return TValue | None with correct type
4. WHEN using cache decorator THEN @cached[TFunc](cache: Generic_Cache) SHALL preserve function signature and return type
5. WHEN serializing values THEN Generic_Serializer[TValue].serialize(value: TValue) SHALL produce JSON that deserializes to equivalent TValue (round-trip property)
6. WHEN using cache patterns THEN Generic_Cache[TKey, TValue].get_or_set(key: TKey, factory: Callable[[], Awaitable[TValue]]) SHALL support cache-aside pattern
7. WHEN invalidating cache THEN Generic_Cache[TKey, TValue].invalidate_pattern(pattern: str) SHALL support pattern-based invalidation
8. WHEN using distributed lock THEN Generic_Lock[TResource].acquire(resource: TResource, timeout: timedelta) SHALL provide typed distributed locking

### Requirement 5: Generic Rate Limiter (Redis)

**User Story:** As a developer, I want a type-safe generic rate limiter, so that I can protect endpoints with configurable limits and typed client identification.

#### Acceptance Criteria

1. WHEN defining Generic_RateLimiter[TClient] THEN TClient SHALL represent the client identifier type (str, UUID, or custom)
2. WHEN checking limits THEN Generic_RateLimiter[TClient].check(client: TClient, limit: RateLimit) SHALL return typed RateLimitResult[TClient]
3. WHEN limit is exceeded THEN RateLimitResult[TClient].is_allowed SHALL be False with retry_after: timedelta
4. WHEN using sliding window THEN Generic_RateLimiter[TClient] SHALL implement sliding window algorithm with configurable window size
5. WHEN using middleware THEN Generic_RateLimitMiddleware[TClient].extract_client(request: Request) SHALL return TClient from request
6. WHEN configuring limits THEN Generic_RateLimiter[TClient].configure(limits: dict[str, RateLimit]) SHALL support per-endpoint limits

### Requirement 6: Generic Repository Pattern (PostgreSQL/SQLModel)

**User Story:** As a developer, I want a type-safe generic repository for PostgreSQL, so that I can perform CRUD operations with compile-time entity type validation.

#### Acceptance Criteria

1. WHEN defining Generic_Repository[TEntity, TId] THEN TEntity SHALL be constrained to SQLModel and TId to comparable types
2. WHEN creating entities THEN Generic_Repository[TEntity, TId].create(entity: TEntity) SHALL return TEntity with generated TId
3. WHEN reading entities THEN Generic_Repository[TEntity, TId].get(id: TId) SHALL return TEntity | None with correct type
4. WHEN updating entities THEN Generic_Repository[TEntity, TId].update(id: TId, entity: TEntity) SHALL return updated TEntity
5. WHEN deleting entities THEN Generic_Repository[TEntity, TId].delete(id: TId) SHALL return bool indicating success
6. WHEN querying entities THEN Generic_Repository[TEntity, TId].query(spec: Specification[TEntity]) SHALL return list[TEntity] with typed specification
7. WHEN using pagination THEN Generic_Repository[TEntity, TId].paginate(page: int, size: int) SHALL return Page[TEntity] with typed pagination
8. WHEN serializing entities THEN Generic_Serializer[TEntity].to_dict(entity: TEntity) SHALL produce dict that reconstructs equivalent TEntity (round-trip property)
9. WHEN using Unit of Work THEN Generic_UnitOfWork.commit() SHALL ensure transactional consistency across multiple Generic_Repository instances

### Requirement 7: Generic NoSQL Repository (ScyllaDB/MongoDB)

**User Story:** As a developer, I want a type-safe generic repository for NoSQL databases, so that I can store documents with flexible schemas and type validation.

#### Acceptance Criteria

1. WHEN defining Generic_DocumentRepository[TDocument, TId] THEN TDocument SHALL be constrained to Pydantic BaseModel
2. WHEN inserting documents THEN Generic_DocumentRepository[TDocument, TId].insert(doc: TDocument) SHALL return TDocument with generated TId
3. WHEN querying documents THEN Generic_DocumentRepository[TDocument, TId].find(filter: Filter[TDocument]) SHALL return list[TDocument] with typed filter
4. WHEN using aggregation THEN Generic_DocumentRepository[TDocument, TId].aggregate(pipeline: Pipeline[TDocument, TResult]) SHALL return list[TResult]
5. WHEN serializing documents THEN Generic_Serializer[TDocument].to_bson(doc: TDocument) SHALL produce BSON that deserializes to equivalent TDocument (round-trip property)
6. WHEN using ScyllaDB THEN Generic_DocumentRepository[TDocument, TId] SHALL support CQL queries with prepared statements

### Requirement 8: Generic Event Handler System

**User Story:** As a developer, I want a type-safe generic event handler system, so that I can implement domain events with compile-time type validation.

#### Acceptance Criteria

1. WHEN defining Generic_EventHandler[TEvent] THEN TEvent SHALL be constrained to DomainEvent base class
2. WHEN handling events THEN Generic_EventHandler[TEvent].handle(event: TEvent) SHALL process only events of type TEvent
3. WHEN dispatching events THEN Generic_EventDispatcher.dispatch(event: TEvent) SHALL route to all registered Generic_EventHandler[TEvent]
4. WHEN using event sourcing THEN Generic_EventStore[TEvent].append(event: TEvent) SHALL persist event with typed metadata
5. WHEN replaying events THEN Generic_EventStore[TEvent].replay(handler: Generic_EventHandler[TEvent]) SHALL replay all TEvent instances
6. WHEN serializing events THEN Generic_Serializer[TEvent].serialize(event: TEvent) SHALL produce JSON that deserializes to equivalent TEvent (round-trip property)

### Requirement 9: Generic HTTP Client with Resilience

**User Story:** As a developer, I want a type-safe generic HTTP client, so that I can call external services with typed requests/responses and built-in resilience.

#### Acceptance Criteria

1. WHEN defining Generic_Client[TRequest, TResponse] THEN both type parameters SHALL be constrained to Pydantic BaseModel
2. WHEN making requests THEN Generic_Client[TRequest, TResponse].call(request: TRequest) SHALL return Awaitable[TResponse] with automatic serialization
3. WHEN response fails validation THEN Generic_Client[TRequest, TResponse] SHALL raise typed ValidationError[TResponse]
4. WHEN using Circuit_Breaker THEN Generic_Client[TRequest, TResponse] SHALL wrap calls with typed CircuitBreaker[TRequest, TResponse]
5. WHEN retrying requests THEN Generic_Client[TRequest, TResponse] SHALL use typed RetryPolicy[TRequest] with exponential backoff
6. WHEN timeout occurs THEN Generic_Client[TRequest, TResponse] SHALL raise typed TimeoutError[TRequest] with request context

### Requirement 10: Generic OpenTelemetry Instrumentation

**User Story:** As a developer, I want generic OpenTelemetry instrumentation, so that I can trace typed operations with automatic span creation.

#### Acceptance Criteria

1. WHEN using @traced decorator THEN @traced[TFunc] SHALL preserve function signature and add span with typed attributes
2. WHEN creating spans THEN Generic_Tracer.start_span[TOperation](operation: TOperation) SHALL create span with typed operation context
3. WHEN adding attributes THEN Generic_Span[TOperation].set_attribute(key: str, value: TValue) SHALL support typed attribute values
4. WHEN propagating context THEN Generic_Tracer.inject[TCarrier](carrier: TCarrier) SHALL inject trace context into typed carrier
5. WHEN extracting context THEN Generic_Tracer.extract[TCarrier](carrier: TCarrier) SHALL extract trace context from typed carrier
6. WHEN exporting traces THEN Generic_Exporter[TSpan] SHALL batch and send to OTLP endpoint

### Requirement 11: Generic Prometheus Metrics

**User Story:** As a developer, I want generic Prometheus metrics, so that I can instrument typed operations with automatic label inference.

#### Acceptance Criteria

1. WHEN defining Generic_Counter[TLabels] THEN TLabels SHALL be a TypedDict or dataclass defining label structure
2. WHEN incrementing counters THEN Generic_Counter[TLabels].inc(labels: TLabels) SHALL validate labels at compile time
3. WHEN observing histograms THEN Generic_Histogram[TLabels].observe(value: float, labels: TLabels) SHALL record with typed labels
4. WHEN using gauges THEN Generic_Gauge[TLabels].set(value: float, labels: TLabels) SHALL set value with typed labels
5. WHEN using @timed decorator THEN @timed[TFunc](histogram: Generic_Histogram) SHALL preserve function signature and record duration
6. WHEN exposing metrics THEN Generic_MetricsExporter SHALL return Prometheus format at /metrics endpoint

### Requirement 12: Generic Structured Logging

**User Story:** As a developer, I want generic structured logging, so that I can log typed events with automatic context binding.

#### Acceptance Criteria

1. WHEN defining Generic_Logger[TContext] THEN TContext SHALL be a TypedDict or dataclass defining log context structure
2. WHEN logging events THEN Generic_Logger[TContext].info(message: str, context: TContext) SHALL include typed context in JSON output
3. WHEN binding context THEN Generic_Logger[TContext].bind(context: TContext) SHALL return new logger with bound typed context
4. WHEN using @logged decorator THEN @logged[TFunc] SHALL log function entry/exit with typed parameters
5. WHEN redacting PII THEN Generic_Logger[TContext] SHALL apply typed PiiRedactor[TContext] before output
6. WHEN outputting logs THEN Generic_Logger[TContext] SHALL format for Loki/Grafana compatibility with ECS fields

### Requirement 13: Generic Authentication System

**User Story:** As a developer, I want a generic authentication system, so that I can secure endpoints with typed user context and claims.

#### Acceptance Criteria

1. WHEN defining Generic_AuthProvider[TUser, TClaims] THEN TUser and TClaims SHALL be Pydantic models
2. WHEN authenticating THEN Generic_AuthProvider[TUser, TClaims].authenticate(credentials: Credentials) SHALL return AuthResult[TUser, TClaims]
3. WHEN validating tokens THEN Generic_AuthProvider[TUser, TClaims].validate(token: str) SHALL return TUser with TClaims or raise typed AuthError
4. WHEN using dependency injection THEN Depends(get_current_user[TUser]) SHALL inject typed TUser into handlers
5. WHEN integrating Keycloak THEN Generic_KeycloakProvider[TUser, TClaims] SHALL map realm roles to TClaims
6. WHEN integrating Auth0 THEN Generic_Auth0Provider[TUser, TClaims] SHALL map custom claims to TClaims
7. WHEN refreshing tokens THEN Generic_AuthProvider[TUser, TClaims].refresh(refresh_token: str) SHALL return new TokenPair[TClaims]

### Requirement 14: Generic RBAC System

**User Story:** As a developer, I want a generic RBAC system, so that I can enforce typed permissions on endpoints with compile-time validation.

#### Acceptance Criteria

1. WHEN defining Generic_Permission[TResource, TAction] THEN TResource and TAction SHALL be Enum types
2. WHEN checking permissions THEN Generic_RBAC[TUser].has_permission(user: TUser, permission: Generic_Permission[TResource, TAction]) SHALL return bool
3. WHEN using @requires decorator THEN @requires[TResource, TAction](permission: Generic_Permission[TResource, TAction]) SHALL enforce typed permission
4. WHEN defining roles THEN Generic_Role[TPermission] SHALL contain set of typed permissions
5. WHEN auditing access THEN Generic_RBAC[TUser] SHALL log typed AuditEvent[TUser, TResource, TAction]

### Requirement 15: Generic Middleware Pipeline

**User Story:** As a developer, I want a generic middleware pipeline, so that I can compose typed middleware with compile-time validation.

#### Acceptance Criteria

1. WHEN defining Generic_Middleware[TContext, TResult] THEN the middleware signature SHALL be Callable[[TContext, Next[TContext, TResult]], Awaitable[TResult]]
2. WHEN composing middleware THEN Generic_Pipeline[TContext, TResult].add(middleware: Generic_Middleware[TContext, TResult]) SHALL build typed pipeline
3. WHEN executing pipeline THEN Generic_Pipeline[TContext, TResult].execute(context: TContext) SHALL return TResult through middleware chain
4. WHEN using request context THEN Generic_RequestContext[TUser] SHALL carry typed user and request metadata
5. WHEN handling errors THEN Generic_ErrorMiddleware[TContext, TError] SHALL catch and transform typed errors

### Requirement 16: Generic Validation System

**User Story:** As a developer, I want a generic validation system, so that I can validate typed inputs with composable validators.

#### Acceptance Criteria

1. WHEN defining Generic_Validator[T] THEN the validator SHALL validate instances of type T
2. WHEN validating THEN Generic_Validator[T].validate(value: T) SHALL return ValidationResult[T] with typed errors
3. WHEN composing validators THEN Generic_Validator[T].and_then(other: Generic_Validator[T]) SHALL chain validators
4. WHEN using Pydantic THEN Generic_PydanticValidator[T] SHALL leverage Pydantic validation with typed errors
5. WHEN validating collections THEN Generic_CollectionValidator[T] SHALL validate list[T] with item-level errors

### Requirement 17: Generic Serialization System

**User Story:** As a developer, I want a generic serialization system, so that I can serialize/deserialize typed objects with format flexibility.

#### Acceptance Criteria

1. WHEN defining Generic_Serializer[T] THEN T SHALL be constrained to Pydantic BaseModel or dataclass
2. WHEN serializing THEN Generic_Serializer[T].serialize(value: T) SHALL produce bytes in configured format (JSON/Avro/MessagePack)
3. WHEN deserializing THEN Generic_Serializer[T].deserialize(data: bytes) SHALL return T or raise typed DeserializationError[T]
4. WHEN round-tripping THEN Generic_Serializer[T].deserialize(Generic_Serializer[T].serialize(value)) SHALL equal original value (round-trip property)
5. WHEN using schema registry THEN Generic_Serializer[T] SHALL register and validate schema derived from T
6. WHEN handling versioning THEN Generic_Serializer[T] SHALL support schema evolution with typed migrations

### Requirement 18: Async-First Architecture

**User Story:** As a developer, I want async-first architecture throughout, so that I can achieve high concurrency with typed async operations.

#### Acceptance Criteria

1. WHEN defining async operations THEN all I/O operations SHALL use async/await with typed Awaitable[T]
2. WHEN using repositories THEN Generic_Repository[TEntity, TId] SHALL provide async methods returning Awaitable[TEntity]
3. WHEN using clients THEN Generic_Client[TRequest, TResponse] SHALL return Awaitable[TResponse]
4. WHEN using streams THEN Generic_AsyncStream[T] SHALL support async iteration with typed items
5. WHEN using task groups THEN Generic_TaskGroup[T] SHALL manage concurrent typed tasks

### Requirement 19: Dependency Injection with Generics

**User Story:** As a developer, I want dependency injection with generic support, so that I can resolve typed dependencies with compile-time validation.

#### Acceptance Criteria

1. WHEN registering dependencies THEN Generic_Container.register[T](factory: Callable[..., T]) SHALL register typed factory
2. WHEN resolving dependencies THEN Generic_Container.resolve[T]() SHALL return instance of T with correct type
3. WHEN using scopes THEN Generic_Container.scoped[T]() SHALL return scoped instance of T
4. WHEN using FastAPI THEN Depends(Generic_Container.resolve[T]) SHALL integrate with FastAPI DI
5. WHEN testing THEN Generic_Container.override[T](mock: T) SHALL allow typed mock injection

### Requirement 20: Docker/Kubernetes Deployment

**User Story:** As a DevOps engineer, I want containerized deployment with Kubernetes, so that I can deploy and scale reliably.

#### Acceptance Criteria

1. WHEN building container THEN Docker_Build SHALL produce minimal image with security scanning
2. WHEN deploying to Kubernetes THEN Helm_Chart SHALL configure resources, probes, and scaling
3. WHEN health checking THEN Probes SHALL verify liveness and readiness of all components
4. WHEN configuring secrets THEN Deployment SHALL use Kubernetes secrets or external vault
5. WHEN scaling THEN HPA SHALL scale based on CPU, memory, and custom metrics

### Requirement 21: CI/CD Pipeline

**User Story:** As a DevOps engineer, I want automated CI/CD, so that I can deploy changes safely.

#### Acceptance Criteria

1. WHEN code is pushed THEN Pipeline SHALL run ruff, mypy/pyright, and pytest
2. WHEN tests pass THEN Pipeline SHALL build and push container image
3. WHEN deploying THEN Pipeline SHALL use rolling update with rollback
4. WHEN security scanning THEN Pipeline SHALL fail on critical vulnerabilities
5. WHEN releasing THEN Pipeline SHALL generate changelog and tag release

### Requirement 22: Serverless-Ready Architecture

**User Story:** As a developer, I want serverless-ready architecture, so that I can deploy to AWS Lambda, Vercel, or Cloudflare Workers.

#### Acceptance Criteria

1. WHEN deploying to AWS Lambda THEN Serverless_Adapter SHALL wrap FastAPI with Mangum
2. WHEN deploying to Vercel THEN Serverless_Adapter SHALL export ASGI application
3. WHEN cold starting THEN Serverless_Adapter SHALL initialize within 500ms
4. WHEN using Generic_Repository[T] THEN Serverless_Adapter SHALL support connection pooling

### Requirement 23: Testing with Property-Based Tests

**User Story:** As a developer, I want comprehensive testing with property-based tests, so that I can verify generic type correctness.

#### Acceptance Criteria

1. WHEN testing Generic_Serializer[T] THEN property tests SHALL verify round-trip for all T instances
2. WHEN testing Generic_Repository[T] THEN property tests SHALL verify CRUD operations preserve entity equality
3. WHEN testing Generic_Cache[TKey, TValue] THEN property tests SHALL verify get after set returns equivalent value
4. WHEN testing Generic_Publisher[T] THEN property tests SHALL verify message serialization round-trip
5. WHEN using Hypothesis THEN property tests SHALL generate typed instances using st.from_type(T)
