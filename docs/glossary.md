# Glossary

## Domain Terms

| Term | Definition |
|------|------------|
| **Aggregate** | A cluster of domain objects that can be treated as a single unit for data changes |
| **Bounded Context** | A logical boundary within which a particular domain model is defined and applicable |
| **Domain Event** | A record of something that happened in the domain that domain experts care about |
| **Entity** | An object defined primarily by its identity rather than its attributes |
| **Repository** | A mechanism for encapsulating storage, retrieval, and search behavior |
| **Specification** | A pattern that encapsulates business rules in a reusable and composable way |
| **Value Object** | An object that describes some characteristic but carries no concept of identity |

## Architecture Terms

| Term | Definition |
|------|------------|
| **Clean Architecture** | An architectural pattern that separates concerns into layers with dependencies pointing inward |
| **CQRS** | Command Query Responsibility Segregation - separating read and write operations |
| **DDD** | Domain-Driven Design - an approach to software development focused on the domain |
| **DTO** | Data Transfer Object - an object that carries data between processes |
| **Use Case** | An application-specific business rule that orchestrates domain logic |

## Technical Terms

| Term | Definition |
|------|------------|
| **Circuit Breaker** | A design pattern that prevents cascading failures in distributed systems |
| **Bulkhead** | A pattern that isolates elements to prevent failures from spreading |
| **JWT** | JSON Web Token - a compact, URL-safe means of representing claims |
| **RBAC** | Role-Based Access Control - restricting system access based on roles |
| **RFC 7807** | Problem Details for HTTP APIs - a standard for error responses |

## Infrastructure Terms

| Term | Definition |
|------|------------|
| **MinIO** | High-performance, S3-compatible object storage |
| **Kafka** | Distributed event streaming platform |
| **RabbitMQ** | Message broker implementing AMQP |
| **Redis** | In-memory data structure store used for caching |
| **Elasticsearch** | Distributed search and analytics engine |
| **ScyllaDB** | High-performance NoSQL database compatible with Cassandra |

## Observability Terms

| Term | Definition |
|------|------------|
| **OpenTelemetry** | Observability framework for traces, metrics, and logs |
| **Span** | A unit of work in distributed tracing |
| **Trace** | A collection of spans representing a request's journey |
| **Correlation ID** | A unique identifier that tracks a request across services |
| **structlog** | A structured logging library for Python |

## Testing Terms

| Term | Definition |
|------|------------|
| **Property-Based Testing** | Testing approach that verifies properties hold for all inputs |
| **Hypothesis** | Python library for property-based testing |
| **polyfactory** | Library for generating test data |
| **Fixture** | A fixed state used as a baseline for running tests |

## Acronyms

| Acronym | Full Form |
|---------|-----------|
| **API** | Application Programming Interface |
| **CRUD** | Create, Read, Update, Delete |
| **DI** | Dependency Injection |
| **HTTP** | Hypertext Transfer Protocol |
| **JSON** | JavaScript Object Notation |
| **ORM** | Object-Relational Mapping |
| **REST** | Representational State Transfer |
| **SQL** | Structured Query Language |
| **TTL** | Time To Live |
| **UUID** | Universally Unique Identifier |
| **ULID** | Universally Unique Lexicographically Sortable Identifier |
