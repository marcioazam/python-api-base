# C4 Container Diagram

## Container View

```mermaid
C4Container
    title Container Diagram - My App

    Person(user, "User", "Application user")
    
    Container_Boundary(myapp, "My App") {
        Container(api, "API", "FastAPI", "REST API endpoints")
        Container(worker, "Worker", "Celery", "Background task processing")
        Container(scheduler, "Scheduler", "Celery Beat", "Periodic tasks")
        
        ContainerDb(db, "Database", "PostgreSQL", "Stores application data")
        ContainerDb(cache, "Cache", "Redis", "Caching and sessions")
        ContainerDb(mq, "Message Queue", "RabbitMQ/Kafka", "Event messaging")
    }
    
    Rel(user, api, "Uses", "HTTPS")
    Rel(api, db, "Reads/Writes", "SQL")
    Rel(api, cache, "Caches", "Redis Protocol")
    Rel(api, mq, "Publishes events", "AMQP/Kafka")
    Rel(worker, mq, "Consumes events", "AMQP/Kafka")
    Rel(worker, db, "Reads/Writes", "SQL")
    Rel(scheduler, mq, "Schedules tasks", "AMQP/Kafka")
```

## Containers

| Container | Technology | Purpose |
|-----------|------------|---------|
| API | FastAPI | REST API endpoints |
| Worker | Celery | Background task processing |
| Scheduler | Celery Beat | Periodic task scheduling |
| Database | PostgreSQL | Primary data store |
| Cache | Redis | Caching and rate limiting |
| Message Queue | RabbitMQ/Kafka | Event-driven messaging |
