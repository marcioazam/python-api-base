# Requirements Document

## Introduction

This specification addresses critical integration issues discovered in the infrastructure modules for the Examples system (ItemExample and PedidoExample). The main problems are:

1. Missing `get_async_session` function referenced by the examples router
2. Router using mock repositories by default instead of real database repositories
3. Incomplete integration preventing manual API testing with data persistence

These fixes will ensure the Examples system is fully functional with real database persistence and can be tested both via automated tests and manual API calls through Docker.

## Glossary

- **Examples System**: Demo implementation of ItemExample and PedidoExample entities showcasing the framework capabilities
- **Router**: FastAPI router that defines API endpoints for the Examples system
- **Repository**: Data access layer that handles database operations for entities
- **DI Container**: Dependency Injection container that manages application dependencies
- **Session**: SQLAlchemy async database session for executing queries
- **Mock Repository**: In-memory fake repository used for testing without database

## Requirements

### Requirement 1

**User Story:** As a developer, I want the database session module to provide an async session generator, so that FastAPI dependency injection can properly inject database sessions into route handlers.

#### Acceptance Criteria

1. WHEN a route handler requests an async session dependency THEN the Infrastructure SHALL provide an `get_async_session` function that yields an AsyncSession
2. WHEN the async session is used THEN the Infrastructure SHALL manage transaction commit and rollback automatically
3. IF the database is not initialized THEN the Infrastructure SHALL raise a DatabaseError with a descriptive message
4. WHEN the session context exits THEN the Infrastructure SHALL close the session properly to prevent connection leaks

### Requirement 2

**User Story:** As a developer, I want the examples router to use real database repositories, so that API calls persist data to the database and can be tested manually.

#### Acceptance Criteria

1. WHEN the examples router handles a request THEN the Router SHALL use real ItemExampleRepository and PedidoExampleRepository instances
2. WHEN creating repository instances THEN the Router SHALL obtain database sessions from the DI system
3. WHEN a repository operation completes THEN the Router SHALL ensure the session is properly committed or rolled back
4. WHEN the API is accessed via Docker THEN the System SHALL persist data to PostgreSQL database

### Requirement 3

**User Story:** As a developer, I want the examples bootstrap to be integrated with the application startup, so that the CQRS handlers for examples are properly registered.

#### Acceptance Criteria

1. WHEN the application starts THEN the System SHALL bootstrap example CQRS handlers alongside user handlers
2. WHEN bootstrapping examples THEN the System SHALL configure CommandBus with validation, retry, and circuit breaker middleware
3. WHEN bootstrapping examples THEN the System SHALL register all Item and Pedido command and query handlers
4. IF bootstrap fails THEN the System SHALL log the error and prevent application startup

### Requirement 4

**User Story:** As a developer, I want to verify the integration works end-to-end, so that I can confidently use the Examples system for demonstrations and testing.

#### Acceptance Criteria

1. WHEN creating an ItemExample via POST /api/v1/examples/items THEN the System SHALL persist the item to the database
2. WHEN retrieving an ItemExample via GET /api/v1/examples/items/{id} THEN the System SHALL return the persisted item
3. WHEN creating a PedidoExample via POST /api/v1/examples/pedidos THEN the System SHALL persist the order to the database
4. WHEN adding items to a PedidoExample THEN the System SHALL update the order in the database with the new items
