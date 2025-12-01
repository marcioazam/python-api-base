# Implementation Plan

**IMPORTANTE: Esta migração usa a abordagem de MOVER arquivos existentes para a nova estrutura, NÃO criar arquivos do zero.**

**NOTA DE ARQUITETURA (Pesquisa 2024/2025):** A estrutura proposta está alinhada com as melhores práticas de:
- Hexagonal Architecture (Ports & Adapters) - Alistair Cockburn
- Clean Architecture - Robert C. Martin
- DDD com Bounded Contexts - Eric Evans
- CQRS + Event Sourcing - Greg Young
- src/ layout - PyPA/pyOpenSci recomendado
- Outbox Pattern - microservices.io
- Repository + Unit of Work - Martin Fowler

## Phase 1: Core Infrastructure Setup

- [x] 1. Create new directory structure and move core files
  - [x] 1.1 Create directory structure for src/my_app with all subdirectories
    - Create src/my_app/ with core/, domain/, application/, interface/, infrastructure/, shared/ directories
    - Create subdirectories as specified in design: core/config, core/types, core/base, core/errors
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 1.2 Move core/config/settings.py with Pydantic Settings v2
    - MOVE src/api/core/config.py → src/my_app/core/config/settings.py
    - Update imports to use my_app namespace
    - _Requirements: 1.1_

  - [x] 1.3 Move core/config/logging.py with structured JSON logging
    - MOVE src/api/infrastructure/logging/config.py → src/my_app/core/config/logging.py
    - Update imports to use my_app namespace
    - _Requirements: 1.2_

  - [x] 1.4 Write property test for configuration loading


    - **Property 1: Configuration Loading from Environment**
    - **Validates: Requirements 1.1**


  - [x] 1.5 Write property test for structured logging with correlation ID

    - **Property 2: Structured JSON Logging with Correlation ID**
    - **Validates: Requirements 1.2**


- [x] 2. Move core base classes
  - [x] 2.1 Move core/base/entity.py with BaseEntity
    - MOVE src/api/shared/entity.py → src/my_app/core/base/entity.py
    - Update imports to use my_app namespace
    - _Requirements: 1.3_

  - [x] 2.2 Move core/base/value_object.py with BaseValueObject
    - MOVE src/api/domain/value_objects/*.py → src/my_app/core/base/value_object.py (consolidate)
    - Update imports to use my_app namespace
    - _Requirements: 1.3_


  - [x] 2.3 Create core/base/aggregate_root.py with AggregateRoot

    - Extend BaseEntity with domain event collection (new file based on existing patterns)
    - _Requirements: 1.3_

  - [x] 2.4 Move core/base/domain_event.py
    - MOVE src/api/shared/events.py → src/my_app/core/base/domain_event.py
    - _Requirements: 1.4_


  - [x] 2.5 Create core/base/integration_event.py

    - Create integration_event.py based on existing patterns for cross-context communication
    - _Requirements: 1.4_

  - [x] 2.6 Write property test for domain events
    - **Property 3: Domain Events Have Timestamp and Unique ID**
    - **Validates: Requirements 1.4**

  - [x] 2.7 Move core/base/repository.py with GenericRepository[T]
    - MOVE src/api/domain/repositories/base.py → src/my_app/core/base/repository.py
    - Update imports to use my_app namespace
    - _Requirements: 1.5_

  - [x] 2.8 Move core/base/use_case.py with GenericUseCase
    - MOVE src/api/shared/use_case.py → src/my_app/core/base/use_case.py
    - Update imports to use my_app namespace
    - _Requirements: 1.6_

  - [x] 2.9 Move core/base/result.py with Result/Either pattern
    - MOVE src/api/shared/result.py → src/my_app/core/base/result.py
    - Update imports to use my_app namespace
    - _Requirements: 1.6_


  - [x] 2.10 Create core/base/command.py with BaseCommand

    - Extract Command base class for CQRS pattern
    - _Requirements: 3.1_

  - [x] 2.11 Create core/base/query.py with BaseQuery


    - Extract Query base class for CQRS pattern
    - _Requirements: 3.2_

  - [x] 2.12 Create core/base/uow.py with UnitOfWork interface


    - Define abstract UnitOfWork interface (Port)
    - _Requirements: 6.3_


- [x] 3. Move and organize core error hierarchy
  - [x] 3.1 Move core/errors/domain_errors.py
    - MOVE src/api/core/exceptions.py → src/my_app/core/errors/ (split into domain/application/infrastructure)
    - Extract domain errors to domain_errors.py
    - _Requirements: 1.7_


  - [x] 3.2 Create core/errors/application_errors.py

    - Extract application errors (ValidationError, AuthorizationError, etc.)
    - _Requirements: 1.7_

  - [x] 3.3 Move core/errors/infrastructure_errors.py
    - MOVE src/api/infrastructure/exceptions.py → src/my_app/core/errors/infrastructure_errors.py
    - _Requirements: 1.7_

- [x] 4. Checkpoint - Ensure all tests pass


  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: Domain Layer (Pure DDD)

- [x] 5. Move domain layer files
  - [x] 5.1 Create domain bounded context directories
    - Created domain/users/, domain/orders/, domain/billing/, domain/common/
    - _Requirements: 2.1_

  - [x] 5.2 Move domain/users/entities.py
    - MOVE src/api/domain/entities/item.py → src/my_app/domain/users/entities.py (adapt for users)
    - _Requirements: 2.2_


  - [x] 5.3 Create domain/users/value_objects.py

    - Create Email, PasswordHash, UserId value objects
    - _Requirements: 2.3_


  - [x] 5.4 Create domain/users/aggregates.py

    - Create UserAggregate extending AggregateRoot (based on existing entity patterns)
    - _Requirements: 2.4_

  - [x] 5.5 Create domain/users/services.py


    - Create domain services for cross-entity operations
    - _Requirements: 2.5_


  - [x] 5.6 Create domain/users/events.py


    - Create UserRegistered, UserDeactivated domain events
    - _Requirements: 2.6_

  - [x] 5.7 Create domain/users/repositories.py (Port interface)


    - Define IUserRepository interface (Port)
    - _Requirements: 2.7_

  - [x] 5.8 Move domain/common/value_objects.py
    - MOVE src/api/domain/value_objects/money.py → src/my_app/domain/common/value_objects.py
    - _Requirements: 2.3_

- [x] 6. Checkpoint - Ensure all tests pass


  - Ensure all tests pass, ask the user if questions arise.


## Phase 3: Application Layer (CQRS)

- [x] 7. Move CQRS infrastructure

  - [x] 7.1 Move application/common/bus.py with CommandBus and QueryBus
    - MOVE src/api/shared/cqrs.py → src/my_app/application/common/bus.py
    - Update imports to use my_app namespace
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 7.2 Write property test for CommandBus middleware

    - **Property 4: CommandBus Dispatches with Middleware**
    - **Validates: Requirements 3.1, 3.3**


  - [x] 7.3 Write property test for QueryBus caching


    - **Property 5: QueryBus Dispatches with Caching**
    - **Validates: Requirements 3.2, 3.4**


  - [x] 7.4 Create application/common/handlers.py

    - Extract handler patterns from existing cqrs.py
    - _Requirements: 3.1, 3.2_


  - [x] 7.5 Create application/common/dto.py


    - Create base DTO classes and PaginatedResponse
    - _Requirements: 3.6_


- [x] 8. Move users application layer
  - [x] 8.1 Create application/users directory structure
    - Created commands/, queries/, handlers/ directories
    - _Requirements: 3.1, 3.2_

  - [x] 8.2 Create application/users/commands/create_user.py

    - Create CreateUserCommand and handler
    - _Requirements: 3.1_



  - [x] 8.3 Create application/users/queries/get_user.py

    - Create GetUserQuery and handler
    - _Requirements: 3.2_



  - [x] 8.4 Create application/users/dto.py

    - Create UserDTO, CreateUserDTO, UpdateUserDTO
    - _Requirements: 3.6_

  - [x] 8.5 Move application/users/mappers.py
    - MOVE src/api/application/mappers/item_mapper.py → src/my_app/application/users/mappers.py
    - _Requirements: 3.5_




  - [x] 8.6 Write property test for mapper round-trip
    - **Property 6: Domain-DTO Mapper Round-Trip**
    - **Validates: Requirements 3.5**

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Read Model and Projections

- [x] 10. Create read model infrastructure
  - [x] 10.1 Create application/read_model/users_read/dto.py


    - Create UserReadDTO based on existing DTO patterns
    - _Requirements: 4.1_


  - [x] 10.2 Create application/projections/users_projections.py



    - Create projection handlers based on existing event patterns


    - _Requirements: 4.2, 4.4_

  - [x] 10.3 Write property test for projections
    - **Property 7: Projections Update Read Models from Events**
    - **Validates: Requirements 4.2**

  - [x] 10.4 Create infrastructure/db/models/read_models.py
    - Create read model based on existing SQLAlchemy patterns
    - _Requirements: 4.3_


- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Interface Layer (Ports)

- [x] 12. Move interface layer files
  - [x] 12.1 Create interface/api directory structure
    - Created v1/, v2/ directories

    - _Requirements: 5.1_

  - [x] 12.2 Move interface/api/v1/ routers

    - MOVE src/api/adapters/api/routes/*.py → src/my_app/interface/api/v1/
    - Update imports to use my_app namespace
    - _Requirements: 5.1_


  - [x] 12.3 Create interface/api/dependencies.py

    - Extract dependency injection patterns from existing routes
    - _Requirements: 5.5_


  - [x] 12.4 Create interface/api/security.py

    - Create OAuth2/JWT security dependencies
    - _Requirements: 5.6_

  - [x] 12.5 Create interface/webhooks directory structure
    - Created inbound/, outbound/ directories

    - _Requirements: 5.2, 5.3_

  - [x] 12.6 Move interface/webhooks/inbound/ handlers

    - MOVE src/api/shared/webhook/*.py → src/my_app/interface/webhooks/inbound/
    - _Requirements: 5.2_

  - [x] 12.7 Create interface/webhooks/outbound/ delivery
    - Create webhook delivery logic with HMAC signing
    - _Requirements: 5.3_

  - [x] 12.8 Create interface/admin/ directory
    - Created admin directory structure
    - _Requirements: 5.4_

  - [x] 12.9 Create interface/main.py FastAPI app
    - Created main.py with FastAPI application factory

    - _Requirements: 5.1_

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: Infrastructure Adapters

- [x] 14. Move database infrastructure
  - [x] 14.1 Create infrastructure/db directory structure
    - Created models/, repositories/, uow/ directories
    - _Requirements: 6.1, 6.2, 6.3_


  - [x] 14.2 Move infrastructure/db/models/

    - MOVE src/api/infrastructure/database/models/*.py → src/my_app/infrastructure/db/models/
    - Update imports to use my_app namespace
    - _Requirements: 6.1_


  - [x] 14.3 Move infrastructure/db/repositories/

    - MOVE src/api/adapters/repositories/*.py → src/my_app/infrastructure/db/repositories/
    - _Requirements: 6.2_


  - [x] 14.4 Move infrastructure/db/uow/

    - MOVE src/api/shared/unit_of_work.py → src/my_app/infrastructure/db/uow/
    - _Requirements: 6.3_

- [x] 15. Move Outbox pattern
  - [x] 15.1 Move infrastructure/outbox/models.py
    - MOVE src/api/shared/outbox.py → src/my_app/infrastructure/outbox/models.py
    - _Requirements: 6.4_


  - [x] 15.2 Create infrastructure/outbox/repository.py

    - Extract OutboxRepository from src/api/shared/outbox.py
    - _Requirements: 6.4_


  - [x] 15.3 Create infrastructure/outbox/dispatcher.py


    - Extract OutboxDispatcher from src/api/shared/outbox.py
    - _Requirements: 6.4_

- [x] 16. Create messaging infrastructure
  - [x] 16.1 Create infrastructure/messaging directory structure
    - Created brokers/, consumers/, dlq/ directories
    - _Requirements: 6.5, 6.6_

  - [x] 16.2 Create infrastructure/messaging/brokers/kafka_broker.py




    - Create Kafka broker interface
    - _Requirements: 6.5_



  - [x] 16.3 Create infrastructure/messaging/brokers/rabbitmq_broker.py

    - Create RabbitMQ broker interface
    - _Requirements: 6.5_



  - [x] 16.4 Create infrastructure/messaging/consumers/base_consumer.py

    - Create base consumer pattern

    - _Requirements: 6.6_


  - [x] 16.5 Create infrastructure/messaging/dlq/handler.py


    - Create DLQ handling based on existing patterns
    - _Requirements: 6.6_

- [x] 17. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 7: Multi-Level Cache

- [x] 18. Move cache infrastructure
  - [x] 18.1 Move infrastructure/cache/providers.py
    - Contains InMemoryCacheProvider and RedisCacheProvider
    - _Requirements: 7.1, 7.2_


  - [x] 18.2 Split infrastructure/cache/local_cache.py


    - Extract InMemoryCacheProvider to dedicated file with LRU implementation
    - _Requirements: 7.1_

  - [x] 18.3 Write property test for LRU cache eviction
    - **Property 8: LRU Cache Eviction Behavior**
    - **Validates: Requirements 7.1**



  - [x] 18.4 Split infrastructure/cache/redis_cache.py
    - Extract RedisCacheProvider to dedicated file
    - _Requirements: 7.2_

  - [x] 18.5 Write property test for cache round-trip
    - **Property 9: Cache Get/Set Round-Trip**
    - **Validates: Requirements 7.2**

  - [x] 18.6 Move infrastructure/cache/policies.py
    - Contains TTL and key strategies
    - _Requirements: 7.3_

  - [x] 18.7 Move infrastructure/cache/decorators.py
    - Contains @cached_query decorator
    - _Requirements: 7.4_


  - [x] 18.8 Write property test for cached decorator
    - **Property 10: Cached Decorator Returns Cached Results**
    - **Validates: Requirements 7.4**

- [x] 19. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 8: Async Tasks and Scheduling

- [x] 20. Create task infrastructure
  - [x] 20.1 Create infrastructure/tasks directory structure
    - Created workers/, schedules/ directories
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 20.2 Create infrastructure/tasks/celery_app.py

    - Create Celery configuration based on existing patterns
    - _Requirements: 8.1_



  - [x] 20.3 Create infrastructure/tasks/workers/rebuild_read_models_task.py


    - Create read model rebuild task
    - _Requirements: 8.4_




  - [x] 20.4 Create infrastructure/tasks/schedules/beat_schedule.py



    - Create periodic task schedules
    - _Requirements: 8.3_

- [x] 21. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 9: Security Infrastructure

- [x] 22. Move security infrastructure
  - [x] 22.1 Move infrastructure/security/password_hashers.py
    - Contains Argon2id implementation
    - _Requirements: 9.1_

  - [x] 22.2 Write property test for password hashing
    - **Property 11: Password Hash Verification**
    - **Validates: Requirements 9.1**

  - [x] 22.3 Move infrastructure/security/token_service.py
    - Contains JWT handling
    - _Requirements: 9.2_

  - [x] 22.4 Write property test for JWT round-trip
    - **Property 12: JWT Encode/Decode Round-Trip**
    - **Validates: Requirements 9.2**

  - [x] 22.5 Move infrastructure/security/rbac.py
    - Contains RBAC implementation
    - _Requirements: 9.3_

  - [x] 22.6 Write property test for RBAC permission composition
    - **Property 13: RBAC Permission Composition**
    - **Validates: Requirements 9.3**

  - [x] 22.7 Move infrastructure/security/rate_limiter.py
    - Contains rate limiting implementation
    - _Requirements: 9.4_

  - [x] 22.8 Move infrastructure/security/sliding_window.py
    - Contains sliding window algorithm
    - _Requirements: 9.4_

  - [x] 22.9 Write property test for rate limiter
    - **Property 14: Rate Limiter Request Counting**
    - **Validates: Requirements 9.4**

  - [x] 22.10 Move infrastructure/security/audit_log.py
    - Contains audit logging

    - _Requirements: 9.5_

  - [x] 22.11 Write property test for audit log persistence
    - **Property 15: Audit Log Entry Persistence**
    - **Validates: Requirements 9.5**

- [x] 23. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 10: Observability Infrastructure

- [x] 24. Move observability infrastructure
  - [x] 24.1 Create infrastructure/observability/logging_config.py
    - Create structured JSON logging configuration
    - _Requirements: 10.1_

  - [x] 24.2 Move infrastructure/observability/metrics.py
    - Contains Prometheus exporters
    - _Requirements: 10.2_

  - [x] 24.3 Create infrastructure/observability/tracing.py
    - Create OpenTelemetry setup
    - _Requirements: 10.3_

  - [x] 24.4 Move infrastructure/observability/correlation_id.py
    - Contains correlation ID propagation
    - _Requirements: 10.4_

- [x] 25. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 11: External HTTP Clients and Storage

- [x] 26. Move HTTP clients
  - [x] 26.1 Move infrastructure/http_clients/retry.py
    - Contains retry logic
    - _Requirements: 11.1_

  - [x] 26.2 Move infrastructure/http_clients/circuit_breaker.py
    - Contains circuit breaker pattern
    - _Requirements: 11.1_

  - [x] 26.3 Create infrastructure/http_clients/base_client.py
    - Create base HTTP client with retry and circuit breaker
    - _Requirements: 11.1_

  - [x] 26.4 Create infrastructure/http_clients/payment_provider_client.py
    - Create payment provider client based on existing patterns
    - _Requirements: 11.2_

  - [x] 26.5 Create infrastructure/http_clients/external_api_client.py
    - Create external API client based on existing patterns
    - _Requirements: 11.3_

- [x] 27. Create storage abstraction
  - [x] 27.1 Create infrastructure/storage directory
    - Created storage directory
    - _Requirements: 12.1, 12.2_

  - [x] 27.2 Create infrastructure/storage/s3_client.py
    - Create S3 storage client based on existing patterns
    - _Requirements: 12.1_

  - [x] 27.3 Create infrastructure/storage/local_storage.py
    - Create local file storage based on existing patterns
    - _Requirements: 12.2_

- [x] 28. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 12: Shared Utilities

- [x] 29. Move shared utilities
  - [x] 29.1 Move shared/utils/time.py
    - Contains time utilities
    - _Requirements: 13.1_

  - [x] 29.2 Move shared/utils/timezone.py
    - Contains timezone utilities
    - _Requirements: 13.1_

  - [x] 29.3 Move shared/utils/ids.py
    - Contains ID generation utilities
    - _Requirements: 13.2_

  - [x] 29.4 Create shared/utils/serialization.py
    - Extract serialization patterns from existing code
    - _Requirements: 13.3_

  - [x] 29.5 Move shared/validation/validators.py
    - Contains validation utilities
    - _Requirements: 13.4_

  - [x] 29.6 Move shared/localization/i18n.py
    - Contains i18n utilities
    - _Requirements: 13.5_

  - [x] 29.7 Move shared/utils/pagination.py
    - Contains pagination utilities
    - _Requirements: 3.6_

  - [x] 29.8 Move shared/utils/password.py
    - Contains password utilities
    - _Requirements: 9.1_

  - [x] 29.9 Move shared/utils/sanitization.py
    - Contains input sanitization utilities
    - _Requirements: 13.4_

  - [x] 29.10 Move shared/utils/safe_pattern.py
    - Contains safe pattern utilities
    - _Requirements: 13.4_

- [x] 30. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.



## Phase 13: Test Organization

- [x] 31. Reorganize test structure
  - [x] 31.1 Move tests/unit/domain/ structure

    - MOVE relevant tests from tests/unit/ → tests/unit/domain/
    - _Requirements: 14.1_

  - [x] 31.2 Move tests/unit/application/ structure

    - MOVE relevant tests from tests/unit/ → tests/unit/application/
    - _Requirements: 14.2_

  - [x] 31.3 Move tests/integration/db/ structure

    - MOVE tests/integration/test_sqlmodel_repository.py → tests/integration/db/
    - _Requirements: 14.3_


  - [x] 31.4 Create tests/integration/messaging/ structure

    - Create messaging integration tests directory
    - _Requirements: 14.4_

  - [x] 31.5 Move tests/e2e/api/ structure
    - MOVE tests/integration/test_*_endpoints.py → tests/e2e/api/
    - _Requirements: 14.5_

  - [x] 31.6 Create tests/e2e/webhooks/ structure
    - Create webhook e2e tests directory
    - _Requirements: 14.6_

  - [x] 31.7 Create tests/contract/ structure
    - Create contract tests directory
    - _Requirements: 14.7_

  - [x] 31.8 Move tests/performance/ structure
    - MOVE tests/load/*.js → tests/performance/
    - _Requirements: 14.8_

- [x] 32. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 14: Deployment Structure

- [x] 33. Move deployment configurations
  - [x] 33.1 Create deployments/docker/ directory
    - Contains api.Dockerfile, docker-compose.yml, docker-compose.prod.yml
    - _Requirements: 15.1_

  - [x] 33.2 Create deployments/docker/worker.Dockerfile
    - Create worker Dockerfile based on existing patterns
    - _Requirements: 15.1_

  - [x] 33.3 Create deployments/docker/scheduler.Dockerfile
    - Create scheduler Dockerfile based on existing patterns
    - _Requirements: 15.1_

  - [x] 33.4 Create deployments/k8s/ directory structure
    - Created base/ directory
    - _Requirements: 15.2_

  - [x] 33.5 Create deployments/k8s subdirectories
    - Create api/, worker/, jobs/, monitoring/, tracing/ subdirectories
    - _Requirements: 15.2_

  - [x] 33.6 Create deployments/ci-cd/ directory
    - Created github-actions/ directory
    - _Requirements: 15.3_

- [x] 34. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 15: Documentation Structure

- [x] 35. Move documentation structure
  - [x] 35.1 Create docs/architecture/ directory
    - Contains overview.md
    - _Requirements: 16.1_


  - [x] 35.2 Create docs/architecture/context-diagram.md

    - Create C4 context diagram
    - _Requirements: 16.1_


  - [x] 35.3 Create docs/architecture/container-diagram.md

    - Create C4 container diagram
    - _Requirements: 16.1_


  - [x] 35.4 Create docs/architecture/component-diagram.md
    - Create C4 component diagram
    - _Requirements: 16.1_

  - [x] 35.5 Create docs/architecture/adr/ directory
    - Created ADR directory

    - _Requirements: 16.2_


  - [x] 35.6 Create docs/api/ directory

    - Create openapi.yaml, security.md, versioning.md based on existing patterns
    - _Requirements: 16.3_


  - [x] 35.7 Create docs/ops/ directory

    - Create observability.md, scaling-strategy.md based on existing patterns
    - _Requirements: 16.4_

- [x] 36. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 16: Module Initialization and Imports

- [x] 37. Add __init__.py files to all modules
  - [x] 37.1 Add __init__.py to core modules
    - Add __init__.py to core/, core/base/, core/errors/, core/types/
    - Export public interfaces
    - _Requirements: 17.2_

  - [x] 37.2 Add __init__.py to domain modules
    - Add __init__.py to domain/, domain/users/, domain/orders/, domain/billing/, domain/common/
    - Export public interfaces
    - _Requirements: 17.2_

  - [x] 37.3 Add __init__.py to application modules
    - Add __init__.py to application/, application/common/, application/users/, etc.
    - Export public interfaces
    - _Requirements: 17.2_

  - [x] 37.4 Add __init__.py to infrastructure modules
    - Add __init__.py to all infrastructure subdirectories
    - Export public interfaces
    - _Requirements: 17.2_

  - [x] 37.5 Add __init__.py to interface modules
    - Add __init__.py to interface/, interface/api/, interface/webhooks/, etc.
    - Export public interfaces
    - _Requirements: 17.2_

  - [x] 37.6 Add __init__.py to shared modules
    - Add __init__.py to shared/, shared/utils/, shared/validation/, shared/localization/
    - Export public interfaces
    - _Requirements: 17.2_

- [x] 38. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 17: Migration and Backward Compatibility


- [x] 39. Ensure migration preservation
  - [x] 39.1 Update all import paths
    - Update imports from src/api to src/my_app in ALL files
    - Update imports from my_api to my_app in ALL files
    - Ensure no broken imports
    - _Requirements: 17.2_

  - [x] 39.2 Verify existing tests pass
    - Run full test suite
    - Fix any broken tests due to import changes
    - _Requirements: 17.3_

  - [x] 39.3 Verify environment variable compatibility
    - Ensure backward compatibility with existing .env files
    - _Requirements: 17.4_

  - [x] 39.4 Write property test for environment variable compatibility
    - **Property 16: Environment Variable Backward Compatibility**
    - **Validates: Requirements 17.4**

- [x] 40. Implement serialization round-trip tests
  - [x] 40.1 Write property test for serialization round-trip
    - **Property 17: Serialization Round-Trip for All Types**
    - Test domain events, DTOs, commands, queries
    - **Validates: Requirements 18.1, 18.2, 18.3**

- [x] 41. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all requirements are covered
  - Run full integration test suite

- [x] 42. Verify complete migration before cleanup
  - [x] 42.1 Audit src/api directory for remaining files
    - src/api directory no longer exists - migration complete
    - _Requirements: 17.1_

  - [x] 42.2 Verify all imports are updated
    - Search for any remaining "from my_api" or "from src.api" imports
    - Search for any remaining "import my_api" or "import src.api" imports
    - Fix any found references
    - _Requirements: 17.2_

  - [x] 42.3 Run comprehensive test suite
    - Run pytest with full coverage
    - Ensure no import errors
    - Ensure no missing module errors
    - _Requirements: 17.3_

  - [x] 42.4 Create migration report
    - Document all files moved from src/api to src/my_app
    - Document any files that were consolidated or split
    - Document any new files created
    - _Requirements: 17.1_

- [x] 43. Rename old src/api directory (preserve for reference)
  - [x] 43.1 src/api directory already removed
    - Migration complete - src/api no longer exists
    - _Requirements: 17.1_

  - [x] 43.2 Final verification after migration
    - Run full test suite one more time
    - Verify application starts correctly with my_app imports
    - Verify all endpoints respond correctly
    - _Requirements: 17.1, 17.3_
