# C4 Component Diagram

## API Component View

```mermaid
flowchart TB
    subgraph Interface["Interface Layer"]
        API[API Routers]
        WH[Webhooks]
        Admin[Admin]
    end
    
    subgraph Application["Application Layer"]
        CB[CommandBus]
        QB[QueryBus]
        Handlers[Handlers]
        Projections[Projections]
    end
    
    subgraph Domain["Domain Layer"]
        Aggregates[Aggregates]
        Entities[Entities]
        Events[Domain Events]
        Services[Domain Services]
    end
    
    subgraph Infrastructure["Infrastructure Layer"]
        DB[(Database)]
        Cache[(Cache)]
        MQ[Message Queue]
        Outbox[Outbox]
    end
    
    API --> CB
    API --> QB
    WH --> CB
    CB --> Handlers
    QB --> Handlers
    Handlers --> Aggregates
    Handlers --> Events
    Events --> Outbox
    Outbox --> MQ
    MQ --> Projections
    Projections --> DB
    QB --> Cache
    QB --> DB
```

## Components

### Interface Layer
- **API Routers**: FastAPI route handlers
- **Webhooks**: Inbound/outbound webhook handlers
- **Admin**: Administrative endpoints

### Application Layer
- **CommandBus**: Dispatches write operations
- **QueryBus**: Dispatches read operations with caching
- **Handlers**: Command and query handlers
- **Projections**: Event handlers for read models

### Domain Layer
- **Aggregates**: Domain aggregate roots
- **Entities**: Domain entities
- **Events**: Domain events
- **Services**: Domain services

### Infrastructure Layer
- **Database**: PostgreSQL persistence
- **Cache**: Redis caching
- **Message Queue**: Event messaging
- **Outbox**: Transactional outbox pattern
