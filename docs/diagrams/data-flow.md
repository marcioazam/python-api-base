# Data Flow Diagrams

Este documento descreve os fluxos de dados principais do Python API Base.

## HTTP Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant MW as Middleware Stack
    participant R as Router
    participant UC as Use Case
    participant D as Domain
    participant REPO as Repository
    participant DB as Database
    
    C->>MW: HTTP Request
    MW->>MW: 1. Logging (correlation_id)
    MW->>MW: 2. CORS validation
    MW->>MW: 3. Security headers
    MW->>MW: 4. Rate limiting
    MW->>MW: 5. JWT validation
    MW->>MW: 6. Audit logging
    MW->>R: Validated Request
    R->>R: Route matching
    R->>R: Request validation (Pydantic)
    R->>UC: Execute Use Case
    UC->>D: Domain Logic
    D->>D: Business Rules
    D->>D: Specifications
    UC->>REPO: Persist/Query
    REPO->>DB: SQL Query
    DB-->>REPO: Result Set
    REPO-->>UC: Entity
    UC->>UC: Map to DTO
    UC-->>R: Response DTO
    R-->>MW: HTTP Response
    MW-->>C: JSON Response
```

## CQRS Command Flow

```mermaid
sequenceDiagram
    participant R as Router
    participant CB as Command Bus
    participant CH as Command Handler
    participant V as Validator
    participant D as Domain
    participant REPO as Repository
    participant EVT as Event Publisher
    
    R->>CB: Dispatch Command
    CB->>CB: Find Handler
    CB->>CH: Execute
    CH->>V: Validate Command
    V-->>CH: Validation Result
    alt Validation Failed
        CH-->>R: Err(ValidationError)
    else Validation Passed
        CH->>D: Create/Update Entity
        D->>D: Apply Business Rules
        CH->>REPO: Persist Entity
        REPO-->>CH: Persisted Entity
        CH->>EVT: Publish Domain Event
        CH-->>R: Ok(Entity)
    end
```

## CQRS Query Flow

```mermaid
sequenceDiagram
    participant R as Router
    participant QB as Query Bus
    participant QH as Query Handler
    participant CACHE as Cache
    participant REPO as Repository
    participant MAP as Mapper
    
    R->>QB: Dispatch Query
    QB->>QB: Find Handler
    QB->>QH: Execute
    QH->>CACHE: Check Cache
    alt Cache Hit
        CACHE-->>QH: Cached Data
    else Cache Miss
        QH->>REPO: Query Data
        REPO-->>QH: Entity
        QH->>CACHE: Store in Cache
    end
    QH->>MAP: Map to DTO
    MAP-->>QH: DTO
    QH-->>R: Response DTO
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant AUTH as Auth Endpoint
    participant JWT as JWT Service
    participant REPO as User Repository
    participant REDIS as Redis (Token Store)
    
    C->>AUTH: POST /auth/login
    AUTH->>REPO: Find User by Email
    REPO-->>AUTH: User Entity
    AUTH->>AUTH: Verify Password
    alt Password Invalid
        AUTH-->>C: 401 Unauthorized
    else Password Valid
        AUTH->>JWT: Create Access Token
        JWT-->>AUTH: Access Token
        AUTH->>JWT: Create Refresh Token
        JWT-->>AUTH: Refresh Token
        AUTH->>REDIS: Store Refresh Token
        AUTH-->>C: {access_token, refresh_token}
    end
```


## Cache Flow

```mermaid
sequenceDiagram
    participant UC as Use Case
    participant DEC as @cached Decorator
    participant CACHE as Cache Provider
    participant REPO as Repository
    
    UC->>DEC: Call cached function
    DEC->>DEC: Build cache key
    DEC->>CACHE: Get from cache
    alt Cache Hit
        CACHE-->>DEC: Cached Value
        DEC-->>UC: Return cached
    else Cache Miss
        DEC->>REPO: Execute original
        REPO-->>DEC: Result
        DEC->>CACHE: Set with TTL
        DEC-->>UC: Return result
    end
```

## Resilience Flow (Circuit Breaker)

```mermaid
stateDiagram-v2
    [*] --> Closed
    
    Closed --> Open: Failure threshold reached
    Closed --> Closed: Success / Failure below threshold
    
    Open --> HalfOpen: Timeout elapsed
    Open --> Open: Requests rejected
    
    HalfOpen --> Closed: Success threshold reached
    HalfOpen --> Open: Any failure
```

## Event Publishing Flow

```mermaid
sequenceDiagram
    participant UC as Use Case
    participant EVT as Event Publisher
    participant KAFKA as Kafka
    participant RABBIT as RabbitMQ
    participant SUB as Subscribers
    
    UC->>EVT: Publish Domain Event
    EVT->>EVT: Serialize Event
    
    par Kafka
        EVT->>KAFKA: Send to Topic
        KAFKA->>SUB: Consume Event
    and RabbitMQ
        EVT->>RABBIT: Publish to Exchange
        RABBIT->>SUB: Deliver to Queue
    end
```

## File Upload Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as Upload Endpoint
    participant VAL as File Validator
    participant MINIO as MinIO
    participant DB as Database
    
    C->>API: POST /upload (multipart)
    API->>VAL: Validate file
    VAL->>VAL: Check size, type, extension
    alt Validation Failed
        VAL-->>API: ValidationError
        API-->>C: 400 Bad Request
    else Validation Passed
        API->>MINIO: Upload file
        MINIO-->>API: Object URL
        API->>DB: Save metadata
        DB-->>API: File record
        API-->>C: 201 Created {url, metadata}
    end
```

## References

- [Architecture Documentation](../architecture.md)
- [CQRS Pattern](../patterns.md#2-cqrs-pattern)
- [Resilience Patterns](../patterns.md#4-resilience-patterns)
