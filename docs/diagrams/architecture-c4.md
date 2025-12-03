# C4 Model - Architecture Diagrams

Este documento contém os diagramas C4 do Python API Base.

## Level 1: System Context

```mermaid
graph TB
    subgraph "External Systems"
        USER[👤 User/Client]
        ADMIN[👤 Admin]
        EXT_API[🌐 External APIs]
    end
    
    subgraph "Python API Base"
        API[🖥️ Python API Base<br/>FastAPI Application]
    end
    
    subgraph "Data Stores"
        DB[(PostgreSQL)]
        CACHE[(Redis)]
        SEARCH[(Elasticsearch)]
        STORAGE[(MinIO/S3)]
    end
    
    subgraph "Messaging"
        KAFKA[Apache Kafka]
        RABBIT[RabbitMQ]
    end
    
    USER -->|HTTP/REST| API
    ADMIN -->|HTTP/REST| API
    API -->|HTTP| EXT_API
    API -->|SQL| DB
    API -->|Cache| CACHE
    API -->|Search| SEARCH
    API -->|Files| STORAGE
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
            CMD[Commands<br/>Write Operations]
            QRY[Queries<br/>Read Operations]
            SVC[Services<br/>Cross-cutting]
        end
        
        subgraph "Domain Layer"
            ENT[Entities]
            VO[Value Objects]
            SPEC[Specifications]
            EVT[Domain Events]
        end
        
        subgraph "Infrastructure Layer"
            REPO[Repositories]
            CACHE_P[Cache Providers]
            MSG[Messaging]
            AUTH[Authentication]
        end
        
        subgraph "Core Layer"
            CFG[Configuration]
            DI[DI Container]
            PROTO[Protocols]
        end
    end
    
    REST --> MW --> CMD
    REST --> MW --> QRY
    GQL --> MW --> CMD
    WS --> MW --> SVC
    
    CMD --> ENT
    QRY --> ENT
    ENT --> VO
    ENT --> SPEC
    
    CMD --> REPO
    QRY --> REPO
    SVC --> CACHE_P
    SVC --> MSG
    
    CFG --> DI
    DI --> REPO
    PROTO --> ENT
```

## Level 3: Component Diagram - Application Layer

```mermaid
graph TB
    subgraph "Application Layer Components"
        subgraph "CQRS"
            CMD_BUS[Command Bus]
            QRY_BUS[Query Bus]
            CMD_H[Command Handlers]
            QRY_H[Query Handlers]
        end
        
        subgraph "Use Cases"
            UC_USER[User Use Cases]
            UC_ITEM[Item Use Cases]
            UC_AUTH[Auth Use Cases]
        end
        
        subgraph "DTOs & Mappers"
            DTO[Data Transfer Objects]
            MAP[Entity Mappers]
        end
        
        subgraph "Services"
            FF[Feature Flags]
            MT[Multitenancy]
            FU[File Upload]
        end
    end
    
    CMD_BUS --> CMD_H
    QRY_BUS --> QRY_H
    CMD_H --> UC_USER
    CMD_H --> UC_ITEM
    CMD_H --> UC_AUTH
    QRY_H --> UC_USER
    QRY_H --> UC_ITEM
    
    UC_USER --> DTO
    UC_ITEM --> DTO
    DTO --> MAP
    
    UC_USER --> FF
    UC_ITEM --> MT
```


## Level 3: Component Diagram - Infrastructure Layer

```mermaid
graph TB
    subgraph "Infrastructure Layer Components"
        subgraph "Database"
            SESSION[Async Session]
            REPO_IMPL[Repository Implementations]
            QB[Query Builder]
            UOW[Unit of Work]
        end
        
        subgraph "Cache"
            CACHE_PROTO[Cache Protocol]
            REDIS_P[Redis Provider]
            MEM_P[Memory Provider]
            CACHE_DEC[@cached Decorator]
        end
        
        subgraph "Messaging"
            KAFKA_P[Kafka Producer]
            KAFKA_C[Kafka Consumer]
            RABBIT_Q[RabbitMQ Queue]
            RABBIT_W[RabbitMQ Worker]
        end
        
        subgraph "Resilience"
            CB[Circuit Breaker]
            RETRY[Retry Pattern]
            BH[Bulkhead]
            TO[Timeout]
        end
        
        subgraph "Auth"
            JWT[JWT Service]
            PWD[Password Policy]
            TOKEN[Token Store]
        end
        
        subgraph "Storage"
            MINIO[MinIO Client]
            UPLOAD[Upload Operations]
            DOWNLOAD[Download Operations]
        end
    end
    
    SESSION --> REPO_IMPL
    REPO_IMPL --> QB
    REPO_IMPL --> UOW
    
    CACHE_PROTO --> REDIS_P
    CACHE_PROTO --> MEM_P
    CACHE_DEC --> CACHE_PROTO
    
    CB --> RETRY
    RETRY --> TO
    
    JWT --> TOKEN
    PWD --> JWT
    
    MINIO --> UPLOAD
    MINIO --> DOWNLOAD
```

## Dependency Flow

```mermaid
graph TD
    INTERFACE[Interface Layer] --> APPLICATION[Application Layer]
    INTERFACE --> INFRASTRUCTURE[Infrastructure Layer]
    APPLICATION --> DOMAIN[Domain Layer]
    APPLICATION --> CORE[Core Layer]
    INFRASTRUCTURE --> DOMAIN
    INFRASTRUCTURE --> CORE
    DOMAIN --> CORE
    
    style CORE fill:#e1f5fe
    style DOMAIN fill:#fff3e0
    style APPLICATION fill:#e8f5e9
    style INFRASTRUCTURE fill:#fce4ec
    style INTERFACE fill:#f3e5f5
```

## References

- [C4 Model](https://c4model.com/)
- [Architecture Documentation](../architecture.md)
- [Layers Documentation](../layers/index.md)
