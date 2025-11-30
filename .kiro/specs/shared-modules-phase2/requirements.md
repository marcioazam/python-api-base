# Requirements Document

## Introduction

Este documento especifica os requisitos para refatoração e melhorias identificadas nos módulos compartilhados da fase 2 (`src/my_api/shared/`). O code review identificou 28 problemas em 10 módulos, incluindo 4 críticos, 10 de alta severidade e 14 de média severidade. As correções visam melhorar segurança, confiabilidade, performance e conformidade com boas práticas Python modernas.

## Glossary

- **Connection Pool**: Conjunto de conexões reutilizáveis para otimizar acesso a recursos externos
- **CSP (Content Security Policy)**: Cabeçalho HTTP de segurança que controla recursos carregados pela página
- **Event Sourcing**: Padrão arquitetural onde mudanças de estado são armazenadas como sequência de eventos
- **Feature Flag**: Mecanismo para habilitar/desabilitar funcionalidades em runtime
- **Fingerprint**: Identificador único gerado a partir de características de uma requisição
- **Fuzzing**: Técnica de teste que gera entradas aleatórias para encontrar bugs
- **GraphQL Federation**: Arquitetura para compor múltiplos serviços GraphQL
- **Hot Reload**: Recarga automática de código em desenvolvimento sem reiniciar servidor
- **Nonce**: Valor único usado uma vez para segurança em CSP
- **Property-Based Testing**: Técnica de teste que verifica propriedades para entradas geradas aleatoriamente

## Requirements

### Requirement 1: Connection Pool Resource Cleanup

**User Story:** As a developer, I want the connection pool to properly cleanup resources, so that connections are not leaked and the system remains stable under load.

#### Acceptance Criteria

1. WHEN a connection exceeds its max_lifetime THEN the ConnectionPool SHALL remove it from the pool and destroy it properly
2. WHEN the pool is closed THEN the ConnectionPool SHALL await all pending connection destructions before returning
3. WHEN a connection health check fails THEN the ConnectionPool SHALL decrement the correct counter (idle, in_use, or unhealthy) before removal
4. WHEN acquiring a connection times out THEN the ConnectionPool SHALL NOT leave the connection in an inconsistent state

### Requirement 2: Connection Pool Statistics Accuracy

**User Story:** As an operations engineer, I want accurate pool statistics, so that I can monitor and tune pool configuration effectively.

#### Acceptance Criteria

1. WHEN connections are acquired and released THEN the PoolStats counters SHALL always reflect the actual pool state
2. WHEN a connection transitions between states THEN the ConnectionPool SHALL update exactly one source counter and one destination counter atomically
3. WHEN the pool is queried for stats THEN the sum of idle, in_use, and unhealthy connections SHALL equal total_connections

### Requirement 3: CSP Nonce Security

**User Story:** As a security engineer, I want CSP nonces to be cryptographically secure, so that attackers cannot predict or forge nonces.

#### Acceptance Criteria

1. WHEN generating a nonce THEN the CSPGenerator SHALL use `secrets.token_urlsafe()` with minimum 16 bytes of entropy
2. WHEN the same route is requested multiple times THEN the CSPGenerator SHALL generate a unique nonce for each request
3. WHEN a nonce is included in the CSP header THEN it SHALL be properly formatted as `'nonce-{base64_value}'`

### Requirement 4: CSP Policy Validation

**User Story:** As a developer, I want CSP policies to be validated, so that invalid configurations fail fast with clear error messages.

#### Acceptance Criteria

1. WHEN a CSP directive contains conflicting keywords (e.g., 'none' with other sources) THEN the CSPBuilder SHALL raise ValueError
2. WHEN an unknown directive is added THEN the CSPPolicy SHALL log a warning but accept it for forward compatibility
3. WHEN the policy is converted to header THEN the CSPPolicy SHALL order directives consistently for caching

### Requirement 5: Event Sourcing Concurrency Safety

**User Story:** As a developer, I want event sourcing operations to be thread-safe, so that concurrent aggregate modifications don't corrupt state.

#### Acceptance Criteria

1. WHEN multiple coroutines save events for the same aggregate concurrently THEN the EventStore SHALL serialize the operations using optimistic locking
2. WHEN a ConcurrencyError occurs THEN the EventStore SHALL include the expected and actual versions in the error message
3. WHEN loading an aggregate with snapshot THEN the EventStore SHALL verify snapshot version matches event stream before applying events

### Requirement 6: Event Sourcing Snapshot Consistency

**User Story:** As a developer, I want snapshots to be consistent with event history, so that aggregate reconstruction is always correct.

#### Acceptance Criteria

1. WHEN a snapshot is created THEN the Snapshot SHALL include a hash of the aggregate state for integrity verification
2. WHEN loading from snapshot THEN the EventStore SHALL validate the state hash before using the snapshot
3. WHEN snapshot validation fails THEN the EventStore SHALL fall back to full event replay and log a warning

### Requirement 7: Feature Flag Percentage Rollout Consistency

**User Story:** As a product manager, I want percentage rollouts to be consistent per user, so that users don't see features flickering on and off.

#### Acceptance Criteria

1. WHEN evaluating a percentage rollout for the same user THEN the FeatureFlagService SHALL return the same result across multiple evaluations
2. WHEN the percentage is changed THEN the FeatureFlagService SHALL maintain consistency for users already in the rollout
3. WHEN no user_id is provided THEN the FeatureFlagService SHALL use a session-based identifier for consistency

### Requirement 8: Feature Flag Audit Trail

**User Story:** As a compliance officer, I want feature flag changes to be auditable, so that we can track who changed what and when.

#### Acceptance Criteria

1. WHEN a flag is enabled, disabled, or modified THEN the FeatureFlagService SHALL emit an audit event with timestamp, actor, and change details
2. WHEN listing flag history THEN the FeatureFlagService SHALL return changes in chronological order
3. WHEN a flag evaluation occurs THEN the FeatureFlagService SHALL optionally log the evaluation context and result

### Requirement 9: Fingerprint Privacy Compliance

**User Story:** As a privacy officer, I want fingerprinting to comply with privacy regulations, so that we don't collect more data than necessary.

#### Acceptance Criteria

1. WHEN generating a fingerprint THEN the FingerprintService SHALL support configurable component exclusion for privacy compliance
2. WHEN IP address is excluded from fingerprint THEN the FingerprintGenerator SHALL still produce a valid fingerprint from remaining components
3. WHEN fingerprint data is stored THEN the FingerprintStore SHALL support configurable TTL for automatic expiration

### Requirement 10: Fingerprint Collision Resistance

**User Story:** As a security engineer, I want fingerprints to have low collision probability, so that different clients are reliably distinguished.

#### Acceptance Criteria

1. WHEN generating fingerprints THEN the FingerprintGenerator SHALL use SHA-256 or stronger hash algorithm
2. WHEN two different request data sets produce the same hash THEN the FingerprintService SHALL detect and log the collision
3. WHEN fingerprint confidence is below threshold THEN the FingerprintService SHALL indicate reduced reliability in the result

### Requirement 11: Fuzzing Input Validation

**User Story:** As a security tester, I want the fuzzer to validate its configuration, so that fuzzing campaigns don't fail due to invalid settings.

#### Acceptance Criteria

1. WHEN FuzzingConfig is created with invalid values THEN the Fuzzer SHALL raise ValueError with descriptive message
2. WHEN corpus_dir or crashes_dir don't exist THEN the Fuzzer SHALL create them with appropriate permissions
3. WHEN max_input_size is less than min_input_size THEN the FuzzingConfig validation SHALL fail

### Requirement 12: Fuzzing Crash Deduplication

**User Story:** As a security tester, I want crash deduplication, so that I don't waste time analyzing duplicate crashes.

#### Acceptance Criteria

1. WHEN a crash is detected THEN the CrashManager SHALL compute a unique crash signature based on error type and stack trace
2. WHEN a duplicate crash is found THEN the CrashManager SHALL increment the occurrence count instead of storing a new crash
3. WHEN listing crashes THEN the CrashManager SHALL group by signature and show occurrence counts

### Requirement 13: Generic CRUD Input Sanitization

**User Story:** As a security engineer, I want all CRUD inputs to be sanitized, so that SQL injection and other attacks are prevented.

#### Acceptance Criteria

1. WHEN filter parameters are parsed THEN the GenericEndpoints SHALL validate field names against allowed model fields
2. WHEN sort parameters are parsed THEN the GenericEndpoints SHALL reject field names not in the model
3. WHEN JSON filter parsing fails THEN the GenericEndpoints SHALL return 400 Bad Request with safe error message

### Requirement 14: Generic CRUD Pagination Limits

**User Story:** As an operations engineer, I want pagination to have enforced limits, so that large queries don't overwhelm the database.

#### Acceptance Criteria

1. WHEN per_page exceeds maximum (100) THEN the GenericEndpoints SHALL cap it at the maximum value
2. WHEN offset would exceed total records THEN the GenericRepository SHALL return empty results without error
3. WHEN counting records for pagination THEN the GenericRepository SHALL use efficient COUNT query without loading entities

### Requirement 15: GraphQL Federation Schema Validation

**User Story:** As a developer, I want federation schemas to be validated, so that composition errors are caught early.

#### Acceptance Criteria

1. WHEN a subgraph is added THEN the FederatedSchema SHALL validate that all @key fields exist in the entity
2. WHEN @requires references a field THEN the FederatedSchema SHALL verify the field is marked @external
3. WHEN schema composition fails validation THEN the FederatedSchema SHALL return all errors, not just the first one

### Requirement 16: GraphQL Federation Entity Resolution

**User Story:** As a developer, I want entity resolution to be type-safe, so that runtime errors are minimized.

#### Acceptance Criteria

1. WHEN resolving entities THEN the FederatedSchema SHALL validate representation format before calling resolver
2. WHEN a resolver is not found for an entity THEN the FederatedSchema SHALL return a clear error instead of empty list
3. WHEN resolver raises an exception THEN the FederatedSchema SHALL wrap it with entity context information

### Requirement 17: Hot Reload Safety Checks

**User Story:** As a developer, I want hot reload to have safety checks, so that production systems are not accidentally affected.

#### Acceptance Criteria

1. WHEN DEBUG environment variable is not set THEN the HotReloadMiddleware SHALL be disabled by default
2. WHEN a reload fails THEN the HotReloadMiddleware SHALL preserve the previous working state
3. WHEN reloading a module with syntax errors THEN the HotReloadMiddleware SHALL log the error and skip the module

### Requirement 18: Hot Reload Dependency Tracking

**User Story:** As a developer, I want hot reload to track dependencies, so that dependent modules are also reloaded when needed.

#### Acceptance Criteria

1. WHEN a module is reloaded THEN the ModuleReloader SHALL identify and reload dependent modules in correct order
2. WHEN circular dependencies exist THEN the ModuleReloader SHALL detect and handle them without infinite loops
3. WHEN dependency resolution fails THEN the ModuleReloader SHALL log the dependency chain and continue with partial reload

### Requirement 19: Contract Testing Response Validation

**User Story:** As a QA engineer, I want comprehensive response validation, so that API contracts are thoroughly verified.

#### Acceptance Criteria

1. WHEN validating response body THEN the ContractTester SHALL support nested field path validation (e.g., "data.user.name")
2. WHEN array responses are validated THEN the ContractTester SHALL support array index access and array matchers
3. WHEN schema validation fails THEN the ContractTester SHALL include the full validation path in error messages

### Requirement 20: Contract Testing OpenAPI Compatibility

**User Story:** As a developer, I want contracts to be compatible with OpenAPI specs, so that I can generate contracts from existing documentation.

#### Acceptance Criteria

1. WHEN generating contracts from OpenAPI THEN the OpenAPIContractValidator SHALL support OpenAPI 3.0 and 3.1 specifications
2. WHEN path parameters are present THEN the OpenAPIContractValidator SHALL correctly match parameterized paths
3. WHEN response schemas are defined THEN the OpenAPIContractValidator SHALL generate appropriate body matchers

### Requirement 21: Unused Import Cleanup Phase 2

**User Story:** As a developer, I want clean imports in all phase 2 modules, so that the codebase is maintainable and follows PEP8 standards.

#### Acceptance Criteria

1. WHEN a module is loaded THEN it SHALL NOT contain unused imports
2. WHEN imports are organized THEN they SHALL follow the order: stdlib, third-party, local
3. WHEN enum modules define only enums THEN they SHALL NOT import unrelated types like `ABC`, `dataclass`, or `Generic`

### Requirement 22: Type Hint Completeness

**User Story:** As a developer, I want complete type hints, so that static analysis tools can catch errors early.

#### Acceptance Criteria

1. WHEN a public function is defined THEN it SHALL have complete parameter and return type hints
2. WHEN generic types are used THEN they SHALL be properly parameterized (e.g., `list[str]` not `list`)
3. WHEN optional parameters have defaults THEN they SHALL use `| None` syntax for Python 3.10+ compatibility

