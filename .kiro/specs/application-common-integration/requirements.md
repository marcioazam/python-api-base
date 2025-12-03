# Requirements Document

## Introduction

This specification defines the integration of `src/application/common` infrastructure components with the `ItemExample` and `PedidoExample` bounded contexts. The goal is to ensure all common components (CQRS buses, middlewares, mappers, batch operations, export services) are fully functional, connected to the application workflow, and testable via the example system.

## Glossary

- **Common Infrastructure**: Shared application layer components in `src/application/common/`
- **ItemExample**: Example bounded context for inventory item management
- **PedidoExample**: Example bounded context for order management
- **CQRS**: Command Query Responsibility Segregation pattern
- **CommandBus**: Dispatcher for write operations (commands)
- **QueryBus**: Dispatcher for read operations (queries)
- **EventBus**: Publisher for domain events
- **Middleware**: Cross-cutting concern handlers (retry, circuit breaker, validation, logging)
- **IMapper**: Interface for entity-to-DTO transformations
- **BatchRepository**: Repository for bulk CRUD operations
- **DataExporter**: Service for multi-format data export (JSON, CSV, JSONL)

## Requirements

### Requirement 1: Unified Error Handling

**User Story:** As a developer, I want all example bounded contexts to use the unified error hierarchy from `application.common.base.exceptions`, so that error handling is consistent across the application.

#### Acceptance Criteria

1. WHEN an error occurs in ItemExample or PedidoExample use cases THEN the system SHALL use error classes from `application.common.base.exceptions`
2. WHEN a NotFoundError is raised THEN the system SHALL include entity_type and entity_id in the error details
3. WHEN a ValidationError is raised THEN the system SHALL include field-level error information
4. WHEN errors are serialized to HTTP responses THEN the system SHALL use the ProblemDetail RFC 7807 format

### Requirement 2: CQRS Integration for ItemExample

**User Story:** As a developer, I want ItemExample operations to use the CQRS pattern with CommandBus and QueryBus, so that the example demonstrates proper command/query separation.

#### Acceptance Criteria

1. WHEN creating an ItemExample THEN the system SHALL dispatch a CreateItemCommand through the CommandBus
2. WHEN updating an ItemExample THEN the system SHALL dispatch an UpdateItemCommand through the CommandBus
3. WHEN deleting an ItemExample THEN the system SHALL dispatch a DeleteItemCommand through the CommandBus
4. WHEN retrieving an ItemExample by ID THEN the system SHALL dispatch a GetItemQuery through the QueryBus
5. WHEN listing ItemExamples THEN the system SHALL dispatch a ListItemsQuery through the QueryBus
6. WHEN a command succeeds THEN the system SHALL publish domain events through the EventBus

### Requirement 3: CQRS Integration for PedidoExample

**User Story:** As a developer, I want PedidoExample operations to use the CQRS pattern with CommandBus and QueryBus, so that the example demonstrates proper command/query separation for complex aggregates.

#### Acceptance Criteria

1. WHEN creating a PedidoExample THEN the system SHALL dispatch a CreatePedidoCommand through the CommandBus
2. WHEN adding an item to a PedidoExample THEN the system SHALL dispatch an AddItemToPedidoCommand through the CommandBus
3. WHEN confirming a PedidoExample THEN the system SHALL dispatch a ConfirmPedidoCommand through the CommandBus
4. WHEN cancelling a PedidoExample THEN the system SHALL dispatch a CancelPedidoCommand through the CommandBus
5. WHEN retrieving a PedidoExample by ID THEN the system SHALL dispatch a GetPedidoQuery through the QueryBus
6. WHEN listing PedidoExamples THEN the system SHALL dispatch a ListPedidosQuery through the QueryBus

### Requirement 4: Mapper Interface Implementation

**User Story:** As a developer, I want ItemExample and PedidoExample mappers to implement the IMapper interface, so that entity-to-DTO transformations follow a consistent pattern.

#### Acceptance Criteria

1. WHEN mapping ItemExample entity to DTO THEN the system SHALL use a mapper implementing IMapper[ItemExample, ItemExampleResponse]
2. WHEN mapping PedidoExample entity to DTO THEN the system SHALL use a mapper implementing IMapper[PedidoExample, PedidoExampleResponse]
3. WHEN mapping a list of entities THEN the system SHALL use the to_dto_list method from IMapper
4. WHEN a mapping error occurs THEN the system SHALL raise MapperError with source and target type information

### Requirement 5: Middleware Pipeline Integration

**User Story:** As a developer, I want the CommandBus to use middleware for cross-cutting concerns, so that retry, circuit breaker, logging, and validation are applied consistently.

#### Acceptance Criteria

1. WHEN the CommandBus is initialized THEN the system SHALL configure LoggingMiddleware for request/response logging
2. WHEN a command fails with a transient error THEN the system SHALL retry using RetryMiddleware with exponential backoff
3. WHEN multiple consecutive failures occur THEN the system SHALL open the circuit breaker to prevent cascade failures
4. WHEN a command has validation rules THEN the system SHALL validate using ValidationMiddleware before execution
5. WHEN middleware executes THEN the system SHALL propagate correlation IDs for distributed tracing

### Requirement 6: Batch Operations Support

**User Story:** As a developer, I want to perform bulk operations on ItemExample entities, so that I can efficiently process large datasets.

#### Acceptance Criteria

1. WHEN bulk creating ItemExamples THEN the system SHALL use BatchRepository with configurable chunk size
2. WHEN bulk updating ItemExamples THEN the system SHALL process updates in batches with progress tracking
3. WHEN bulk deleting ItemExamples THEN the system SHALL support both soft and hard delete modes
4. WHEN a batch operation fails partially THEN the system SHALL return BatchResult with succeeded and failed items
5. WHEN using CONTINUE error strategy THEN the system SHALL process all items and collect errors

### Requirement 7: Data Export/Import Support

**User Story:** As a developer, I want to export and import ItemExample data in multiple formats, so that I can integrate with external systems.

#### Acceptance Criteria

1. WHEN exporting ItemExamples to JSON THEN the system SHALL include metadata with export timestamp and record count
2. WHEN exporting ItemExamples to CSV THEN the system SHALL generate valid CSV with headers
3. WHEN exporting ItemExamples to JSONL THEN the system SHALL generate one JSON object per line
4. WHEN importing data THEN the system SHALL return ImportResult with processed, imported, skipped, and failed counts
5. WHEN export completes THEN the system SHALL compute SHA-256 checksum for data integrity verification

### Requirement 8: API Router Integration

**User Story:** As a developer, I want the example API routes to use dependency injection for CQRS buses, so that the routes are testable and follow clean architecture.

#### Acceptance Criteria

1. WHEN an API endpoint receives a request THEN the system SHALL inject CommandBus and QueryBus via FastAPI dependencies
2. WHEN the API returns a response THEN the system SHALL wrap data in ApiResponse or PaginatedResponse from common DTOs
3. WHEN an error occurs THEN the system SHALL return ProblemDetail response with appropriate HTTP status code
4. WHEN listing entities THEN the system SHALL support pagination with page, size, and total fields

### Requirement 9: Unit and Integration Tests

**User Story:** As a developer, I want comprehensive tests for the integrated example system, so that I can verify all components work together correctly.

#### Acceptance Criteria

1. WHEN running unit tests THEN the system SHALL test each command handler in isolation
2. WHEN running unit tests THEN the system SHALL test each query handler in isolation
3. WHEN running integration tests THEN the system SHALL test the full request-response cycle through the API
4. WHEN running tests THEN the system SHALL achieve minimum 80% code coverage for example bounded contexts
5. WHEN testing middleware THEN the system SHALL verify retry, circuit breaker, and logging behavior
