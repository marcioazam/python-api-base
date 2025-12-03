# Data Flows

## Request Flow

### HTTP Request Lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant MW as Middleware Stack
    participant R as Router
    participant UC as Use Case
    participant D as Domain
    participant I as Infrastructure
    participant DB as Database
    
    C->>MW: HTTP Request
    MW->>MW: 1. Correlation ID
    MW->>MW: 2. Security Headers
    MW->>MW: 3. Rate Limiting
    MW->>MW: 4. Authentication
    MW->>MW: 5. Logging
    MW->>R: Validated Request
    R->>UC: Execute Use Case
    UC->>D: Domain Logic
    D->>D: Validate Business Rules
    D->>D: Apply Specifications
    UC->>I: Persist/Query
    I->>DB: SQL Query
    DB-->>I: Result
    I-->>UC: Entity
    UC->>UC: Map to DTO
    UC-->>R: Response DTO
    R-->>MW: HTTP Response
    MW->>MW: Add Response Headers
    MW-->>C: HTTP Response
```

### Middleware Execution Order

```mermaid
flowchart LR
    A[Request] --> B[CorrelationID]
    B --> C[SecurityHeaders]
    C --> D[RateLimit]
    D --> E[Authentication]
    E --> F[Logging]
    F --> G[Router]
    G --> H[Response]
```

## Authentication Flow

### JWT Authentication

```mermaid
sequenceDiagram
    participant C as Client
    participant API as API
    participant AUTH as Auth Service
    participant REDIS as Redis
    participant DB as Database
    
    C->>API: POST /auth/login (credentials)
    API->>AUTH: Validate credentials
    AUTH->>DB: Get user
    DB-->>AUTH: User data
    AUTH->>AUTH: Verify password
    AUTH->>AUTH: Generate tokens
    AUTH->>REDIS: Store refresh token
    AUTH-->>API: Access + Refresh tokens
    API-->>C: 200 OK (tokens)
    
    Note over C,API: Subsequent requests
    
    C->>API: GET /resource (Bearer token)
    API->>AUTH: Validate token
    AUTH->>AUTH: Verify signature
    AUTH->>REDIS: Check revocation
    REDIS-->>AUTH: Not revoked
    AUTH-->>API: Valid (user claims)
    API-->>C: 200 OK (resource)
```

### Token Refresh Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as API
    participant AUTH as Auth Service
    participant REDIS as Redis
    
    C->>API: POST /auth/refresh (refresh_token)
    API->>AUTH: Validate refresh token
    AUTH->>REDIS: Check token exists
    REDIS-->>AUTH: Token valid
    AUTH->>AUTH: Generate new access token
    AUTH-->>API: New access token
    API-->>C: 200 OK (new token)
```

## CQRS Flow

### Command Flow

```mermaid
sequenceDiagram
    participant R as Router
    participant CB as Command Bus
    participant CH as Command Handler
    participant D as Domain
    participant REPO as Repository
    participant EB as Event Bus
    
    R->>CB: Dispatch Command
    CB->>CB: Validate Command
    CB->>CH: Execute Handler
    CH->>D: Create/Update Entity
    D->>D: Apply Business Rules
    D->>D: Generate Domain Events
    CH->>REPO: Persist Entity
    REPO-->>CH: Success
    CH->>EB: Publish Events
    EB-->>CH: Events Published
    CH-->>CB: Result
    CB-->>R: Command Result
```

### Query Flow

```mermaid
sequenceDiagram
    participant R as Router
    participant QB as Query Bus
    participant QH as Query Handler
    participant CACHE as Cache
    participant REPO as Repository
    
    R->>QB: Dispatch Query
    QB->>QH: Execute Handler
    QH->>CACHE: Check Cache
    alt Cache Hit
        CACHE-->>QH: Cached Data
    else Cache Miss
        QH->>REPO: Query Database
        REPO-->>QH: Data
        QH->>CACHE: Store in Cache
    end
    QH->>QH: Map to DTO
    QH-->>QB: Query Result
    QB-->>R: Response DTO
```

## Domain Event Flow

```mermaid
sequenceDiagram
    participant UC as Use Case
    participant AGG as Aggregate
    participant EB as Event Bus
    participant H1 as Handler 1
    participant H2 as Handler 2
    participant KAFKA as Kafka
    
    UC->>AGG: Execute Operation
    AGG->>AGG: Apply Business Logic
    AGG->>AGG: Record Domain Event
    UC->>EB: Publish Events
    
    par Async Handlers
        EB->>H1: Handle Event
        H1->>H1: Process
    and
        EB->>H2: Handle Event
        H2->>H2: Process
    and
        EB->>KAFKA: Publish to Topic
    end
```

## Cache Flow

### Cache-Aside Pattern

```mermaid
flowchart TD
    A[Request] --> B{Cache Hit?}
    B -->|Yes| C[Return Cached]
    B -->|No| D[Query Database]
    D --> E[Store in Cache]
    E --> F[Return Data]
    C --> G[Response]
    F --> G
```

### Cache Invalidation

```mermaid
sequenceDiagram
    participant UC as Use Case
    participant REPO as Repository
    participant CACHE as Cache
    participant DB as Database
    
    UC->>REPO: Update Entity
    REPO->>DB: Execute Update
    DB-->>REPO: Success
    REPO->>CACHE: Invalidate Key
    CACHE-->>REPO: Invalidated
    REPO->>CACHE: Invalidate Pattern
    CACHE-->>REPO: Pattern Cleared
    REPO-->>UC: Success
```

## Error Flow

```mermaid
flowchart TD
    A[Exception Raised] --> B{Exception Type}
    B -->|Domain| C[DomainError]
    B -->|Validation| D[ValidationError]
    B -->|NotFound| E[NotFoundError]
    B -->|Auth| F[AuthError]
    B -->|Infrastructure| G[InfraError]
    
    C --> H[Error Handler]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I[RFC 7807 Format]
    I --> J[Log Error]
    J --> K[HTTP Response]
```

## Related Documentation

- [C4 Model](c4-model.md)
- [Dependencies](dependencies.md)
- [Error Handling](../layers/interface/error-handling.md)
