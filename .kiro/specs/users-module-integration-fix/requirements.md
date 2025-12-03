# Requirements Document

## Introduction

O módulo `src/application/users` implementa CQRS para gerenciamento de usuários, porém está desconectado do workflow principal da aplicação. Existem dois routers conflitantes com o mesmo prefixo `/users`: um usando CQRS real (`interface/v1/users_router.py`) e outro usando mock storage (`interface/v1/auth/users_router.py`). O `main.py` importa o router com mock, deixando o código CQRS órfão. Além disso, os testes de propriedades têm imports incorretos (`my_app` em vez de `application`).

## Glossary

- **System**: O módulo de Users da aplicação Python API Base
- **CQRS**: Command Query Responsibility Segregation - padrão que separa operações de leitura e escrita
- **Router**: Componente FastAPI que define endpoints HTTP
- **Mock Storage**: Armazenamento em memória para desenvolvimento/testes
- **UserAggregate**: Aggregate root do domínio de usuários
- **UserMapper**: Componente que converte entre UserAggregate e UserDTO
- **Property-Based Test**: Teste que verifica propriedades universais usando geração de dados aleatórios

## Requirements

### Requirement 1: Resolução de Conflito de Routers

**User Story:** As a developer, I want a single users router that uses the CQRS implementation, so that user operations are persisted correctly and the codebase has no conflicting routes.

#### Acceptance Criteria

1. WHEN the application starts THEN the System SHALL register only one `/users` router that uses CQRS handlers
2. WHEN a user creates a new user via POST `/api/v1/users` THEN the System SHALL dispatch CreateUserCommand through the CommandBus
3. WHEN a user queries users via GET `/api/v1/users` THEN the System SHALL dispatch ListUsersQuery through the QueryBus
4. WHEN the mock-based users_router is removed THEN the System SHALL maintain all existing endpoint signatures for backward compatibility

### Requirement 2: Correção de Imports nos Testes

**User Story:** As a developer, I want the property-based tests to use correct imports, so that tests can execute and validate the UserMapper functionality.

#### Acceptance Criteria

1. WHEN running `test_mapper_roundtrip_properties.py` THEN the System SHALL import UserMapper from `application.users.commands.mapper`
2. WHEN running `test_mapper_roundtrip_properties.py` THEN the System SHALL import UserDTO from `application.users.commands.dtos`
3. WHEN running `test_mapper_roundtrip_properties.py` THEN the System SHALL import UserAggregate from `domain.users.aggregates`
4. WHEN all imports are corrected THEN the System SHALL execute all property tests without ImportError

### Requirement 3: Integração do Router CQRS no Main

**User Story:** As a developer, I want the main.py to use the CQRS-based users router, so that user operations flow through the proper application layer.

#### Acceptance Criteria

1. WHEN main.py imports users_router THEN the System SHALL import from `interface.v1.users_router` instead of `interface.v1.auth`
2. WHEN the CQRS router is integrated THEN the System SHALL maintain the `/api/v1/users` prefix
3. WHEN auth functionality is needed THEN the System SHALL keep auth_router separate from users_router

### Requirement 4: Validação de Round-Trip do Mapper

**User Story:** As a developer, I want property-based tests to validate UserMapper round-trip, so that I have confidence in domain-DTO conversions.

#### Acceptance Criteria

1. WHEN converting UserAggregate to UserDTO THEN the System SHALL preserve all public fields (id, email, username, display_name, is_active, is_verified, created_at, updated_at)
2. WHEN converting UserDTO to UserAggregate THEN the System SHALL preserve all DTO fields except password_hash
3. WHEN performing round-trip conversion (Aggregate → DTO → Aggregate) THEN the System SHALL produce equivalent objects for all DTO-visible fields
