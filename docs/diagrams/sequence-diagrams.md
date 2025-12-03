# Sequence Diagrams

Este documento contém diagramas de sequência para os principais fluxos do sistema.

## User Registration

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router
    participant CMD as CreateUserCommand
    participant VAL as Validator
    participant REPO as UserRepository
    participant PWD as PasswordPolicy
    participant EVT as EventPublisher
    participant DB as Database
    
    C->>R: POST /api/v1/users
    R->>R: Validate request body
    R->>CMD: Create command
    CMD->>VAL: Validate email format
    CMD->>REPO: Check email exists
    REPO->>DB: SELECT by email
    DB-->>REPO: null
    REPO-->>CMD: false
    CMD->>PWD: Validate password
    PWD-->>CMD: Valid
    CMD->>PWD: Hash password
    PWD-->>CMD: Hashed password
    CMD->>REPO: Create user
    REPO->>DB: INSERT
    DB-->>REPO: User record
    REPO-->>CMD: User entity
    CMD->>EVT: Publish UserCreated
    CMD-->>R: Ok(User)
    R-->>C: 201 Created
```

## Item CRUD Operations

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router
    participant UC as Use Case
    participant SPEC as Specification
    participant REPO as Repository
    participant CACHE as Cache
    participant DB as Database
    
    Note over C,DB: CREATE
    C->>R: POST /api/v1/items
    R->>UC: CreateItemCommand
    UC->>REPO: Create
    REPO->>DB: INSERT
    DB-->>REPO: Item
    UC->>CACHE: Invalidate list cache
    UC-->>R: Item DTO
    R-->>C: 201 Created
    
    Note over C,DB: READ (with cache)
    C->>R: GET /api/v1/items/{id}
    R->>UC: GetItemQuery
    UC->>CACHE: Get item:{id}
    alt Cache Hit
        CACHE-->>UC: Cached item
    else Cache Miss
        UC->>REPO: Get by ID
        REPO->>DB: SELECT
        DB-->>REPO: Item
        UC->>CACHE: Set item:{id}
    end
    UC-->>R: Item DTO
    R-->>C: 200 OK
    
    Note over C,DB: LIST (with specification)
    C->>R: GET /api/v1/items?status=active
    R->>UC: ListItemsQuery
    UC->>SPEC: Build specification
    SPEC-->>UC: ActiveItemSpec
    UC->>REPO: Find by spec
    REPO->>DB: SELECT WHERE
    DB-->>REPO: Items[]
    UC-->>R: Item DTOs[]
    R-->>C: 200 OK
```

## Token Refresh Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router
    participant JWT as JWT Service
    participant REDIS as Redis
    participant REPO as UserRepository
    
    C->>R: POST /auth/refresh
    R->>JWT: Verify refresh token
    JWT->>JWT: Decode token
    alt Token Invalid
        JWT-->>R: TokenError
        R-->>C: 401 Unauthorized
    else Token Valid
        JWT->>REDIS: Check token exists
        alt Token Revoked
            REDIS-->>JWT: null
            JWT-->>R: TokenRevokedError
            R-->>C: 401 Unauthorized
        else Token Active
            REDIS-->>JWT: token data
            JWT->>REPO: Get user
            REPO-->>JWT: User
            JWT->>JWT: Create new access token
            JWT->>REDIS: Rotate refresh token
            JWT-->>R: {access_token, refresh_token}
            R-->>C: 200 OK
        end
    end
```


## Specification Pattern Usage

```mermaid
sequenceDiagram
    participant UC as Use Case
    participant SPEC as Specification Builder
    participant CONV as SQLAlchemy Converter
    participant REPO as Repository
    participant DB as Database
    
    UC->>SPEC: Build complex spec
    SPEC->>SPEC: equals("status", "active")
    SPEC->>SPEC: .and_spec(greater_than("price", 100))
    SPEC->>SPEC: .and_spec(is_null("deleted_at"))
    SPEC-->>UC: CompositeSpecification
    
    UC->>REPO: Find by specification
    REPO->>CONV: Convert to SQLAlchemy
    CONV->>CONV: Build WHERE clause
    CONV-->>REPO: SQLAlchemy filter
    REPO->>DB: SELECT ... WHERE ...
    DB-->>REPO: Results
    REPO-->>UC: Entities
```

## Circuit Breaker in Action

```mermaid
sequenceDiagram
    participant UC as Use Case
    participant CB as Circuit Breaker
    participant EXT as External Service
    
    Note over UC,EXT: Normal Operation (Closed)
    UC->>CB: Execute call
    CB->>EXT: HTTP Request
    EXT-->>CB: Success
    CB-->>UC: Result
    
    Note over UC,EXT: Failures Accumulate
    UC->>CB: Execute call
    CB->>EXT: HTTP Request
    EXT-->>CB: Error (failure 1)
    CB-->>UC: Error
    
    UC->>CB: Execute call
    CB->>EXT: HTTP Request
    EXT-->>CB: Error (failure 5 - threshold)
    CB->>CB: State -> OPEN
    CB-->>UC: Error
    
    Note over UC,EXT: Circuit Open
    UC->>CB: Execute call
    CB-->>UC: CircuitOpenError (fast fail)
    
    Note over UC,EXT: After Timeout (Half-Open)
    UC->>CB: Execute call
    CB->>CB: State -> HALF_OPEN
    CB->>EXT: HTTP Request (test)
    EXT-->>CB: Success
    CB->>CB: State -> CLOSED
    CB-->>UC: Result
```

## Batch Processing

```mermaid
sequenceDiagram
    participant API as API
    participant BATCH as Batch Processor
    participant UOW as Unit of Work
    participant REPO as Repository
    participant DB as Database
    
    API->>BATCH: Process items[]
    BATCH->>UOW: Begin transaction
    
    loop For each item
        BATCH->>REPO: Create/Update
        REPO->>DB: SQL Operation
        alt Error
            DB-->>REPO: Error
            REPO-->>BATCH: Error
            BATCH->>UOW: Rollback
            UOW->>DB: ROLLBACK
            BATCH-->>API: BatchError
        else Success
            DB-->>REPO: OK
        end
    end
    
    BATCH->>UOW: Commit
    UOW->>DB: COMMIT
    BATCH-->>API: BatchResult
```

## WebSocket Connection

```mermaid
sequenceDiagram
    participant C as Client
    participant WS as WebSocket Handler
    participant AUTH as Auth Service
    participant MGR as Connection Manager
    participant PUB as Event Publisher
    
    C->>WS: Connect (with token)
    WS->>AUTH: Validate token
    AUTH-->>WS: User info
    WS->>MGR: Register connection
    MGR-->>WS: Connection ID
    WS-->>C: Connected
    
    loop Message Loop
        C->>WS: Send message
        WS->>WS: Process message
        WS->>PUB: Broadcast event
        PUB->>MGR: Get subscribers
        MGR-->>PUB: Connections[]
        PUB->>C: Push to clients
    end
    
    C->>WS: Disconnect
    WS->>MGR: Unregister
    WS-->>C: Closed
```

## References

- [Architecture Documentation](../architecture.md)
- [Data Flow Diagrams](data-flow.md)
- [C4 Model](architecture-c4.md)
