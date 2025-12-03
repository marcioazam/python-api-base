# C4 Model Diagrams

## Level 1: System Context

```mermaid
graph TB
    subgraph "External Systems"
        USER[👤 User/Client]
        ADMIN[👤 Admin]
        EXT_SVC[External Services]
    end
    
    subgraph "Python API Base"
        API[Python API Base<br/>REST/GraphQL/WebSocket API]
    end
    
    subgraph "Data Stores"
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        ES[(Elasticsearch)]
        MINIO[(MinIO/S3)]
    end
    
    subgraph "Messaging"
        KAFKA[Kafka]
        RABBIT[RabbitMQ]
    end
    
    USER -->|HTTP/WS| API
    ADMIN -->|HTTP| API
    API -->|HTTP| EXT_SVC
    API -->|SQL| PG
    API -->|Cache| REDIS
    API -->|Search| ES
    API -->|Storage| MINIO
    API -->|Events| KAFKA
    API -->|Tasks| RABBIT
```

## Level 2: Container Diagram

```mermaid
graph TB
    subgraph "Python API Base"
        subgraph "Interface Layer"
            REST[REST API<br/>FastAPI Routers]
            GQL[GraphQL<br/>Strawberry]
            WS[WebSocket<br/>Handlers]
            MW[Middleware Stack]
        end
        
        subgraph "Application Layer"
            UC[Use Cases]
            CMD[Commands]
            QRY[Queries]
            SVC[Services]
        end
        
        subgraph "Domain Layer"
            ENT[Entities]
            VO[Value Objects]
            SPEC[Specifications]
            EVT[Domain Events]
        end
        
        subgraph "Infrastructure Layer"
            DB_REPO[DB Repositories]
            CACHE_PROV[Cache Providers]
            MSG_PROD[Message Producers]
            AUTH[Auth Services]
        end
        
        subgraph "Core Layer"
            CFG[Configuration]
            DI[DI Container]
            PROTO[Protocols]
            TYPES[Type Definitions]
        end
    end
    
    REST --> MW
    GQL --> MW
    WS --> MW
    MW --> UC
    UC --> CMD
    UC --> QRY
    UC --> SVC
    CMD --> ENT
    QRY --> ENT
    ENT --> VO
    ENT --> SPEC
    ENT --> EVT
    UC --> DB_REPO
    UC --> CACHE_PROV
    UC --> MSG_PROD
    UC --> AUTH
    CFG --> UC
    DI --> UC
    PROTO --> ENT
```

## Level 3: Component Diagram - Core Layer

```mermaid
graph TB
    subgraph "Core Layer"
        subgraph "base/"
            BASE_CQRS[CQRS Base]
            BASE_DOMAIN[Domain Base]
            BASE_EVENTS[Events Base]
            BASE_PATTERNS[Patterns Base]
            BASE_REPO[Repository Base]
        end
        
        subgraph "config/"
            SETTINGS[Settings]
            DB_CFG[Database Config]
            SEC_CFG[Security Config]
            OBS_CFG[Observability Config]
        end
        
        subgraph "di/"
            CONTAINER[Container]
            RESOLVER[Resolver]
            SCOPES[Scopes]
            LIFECYCLE[Lifecycle]
        end
        
        subgraph "errors/"
            BASE_ERR[Base Errors]
            HTTP_ERR[HTTP Errors]
            SHARED_ERR[Shared Errors]
        end
        
        subgraph "protocols/"
            APP_PROTO[Application Protocols]
            DATA_PROTO[Data Access Protocols]
            ENTITY_PROTO[Entity Protocols]
            REPO_PROTO[Repository Protocols]
        end
        
        subgraph "types/"
            ID_TYPES[ID Types]
            JSON_TYPES[JSON Types]
            RESULT_TYPES[Result Types]
            SEC_TYPES[Security Types]
        end
    end
    
    SETTINGS --> DB_CFG
    SETTINGS --> SEC_CFG
    SETTINGS --> OBS_CFG
    CONTAINER --> RESOLVER
    CONTAINER --> SCOPES
    CONTAINER --> LIFECYCLE
```

## Level 3: Component Diagram - Infrastructure Layer

```mermaid
graph TB
    subgraph "Infrastructure Layer"
        subgraph "Database"
            SESSION[Session Manager]
            QUERY_BUILDER[Query Builder]
            REPOSITORIES[Repositories]
            MIGRATIONS[Migrations]
            UOW[Unit of Work]
        end
        
        subgraph "Cache"
            REDIS_PROV[Redis Provider]
            MEM_PROV[Memory Provider]
            CACHE_DEC[Cache Decorators]
        end
        
        subgraph "Messaging"
            KAFKA_PROD[Kafka Producer]
            KAFKA_CONS[Kafka Consumer]
            RABBIT_QUEUE[RabbitMQ Queue]
            RABBIT_WORKER[RabbitMQ Worker]
        end
        
        subgraph "Auth"
            JWT_SVC[JWT Service]
            PWD_POLICY[Password Policy]
            TOKEN_STORE[Token Store]
        end
        
        subgraph "Resilience"
            CIRCUIT[Circuit Breaker]
            RETRY[Retry]
            BULKHEAD[Bulkhead]
        end
        
        subgraph "Observability"
            TELEMETRY[Telemetry]
            LOGGING[Logging]
            METRICS[Metrics]
            TRACING[Tracing]
        end
    end
    
    SESSION --> QUERY_BUILDER
    SESSION --> REPOSITORIES
    SESSION --> UOW
    REDIS_PROV --> CACHE_DEC
    MEM_PROV --> CACHE_DEC
```

## Level 3: Component Diagram - Interface Layer

```mermaid
graph TB
    subgraph "Interface Layer"
        subgraph "REST API"
            V1[v1 Endpoints]
            V2[v2 Endpoints]
            HEALTH[Health Router]
        end
        
        subgraph "GraphQL"
            SCHEMA[Schema]
            RESOLVERS[Resolvers]
            DATALOADERS[DataLoaders]
        end
        
        subgraph "WebSocket"
            WS_HANDLERS[Handlers]
            WS_CHAT[Chat]
        end
        
        subgraph "Middleware"
            SEC_MW[Security Middleware]
            LOG_MW[Logging Middleware]
            REQ_MW[Request Middleware]
        end
        
        subgraph "Versioning"
            VER_STRATEGY[Versioning Strategy]
            DEPRECATION[Deprecation Handler]
        end
        
        subgraph "Errors"
            ERR_HANDLERS[Error Handlers]
            RFC7807[RFC 7807 Formatter]
        end
    end
    
    V1 --> SEC_MW
    V2 --> SEC_MW
    SCHEMA --> RESOLVERS
    RESOLVERS --> DATALOADERS
    SEC_MW --> LOG_MW
    LOG_MW --> REQ_MW
```

## Related Documentation

- [Data Flows](data-flows.md)
- [Dependencies](dependencies.md)
- [Layers Documentation](../layers/index.md)
