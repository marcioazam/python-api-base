"""Core base classes for the application.

Provides foundational patterns:
- Domain: Entity, Aggregate, ValueObject
- Events: DomainEvent, IntegrationEvent
- Repository: IRepository, InMemoryRepository
- CQRS: Command, Query
- Patterns: Result, Specification, Validation

**Feature: architecture-restructuring-2025**
"""

# Domain building blocks
from core.base.domain import (
    BaseEntity,
    AuditableEntity,
    VersionedEntity,
    AuditableVersionedEntity,
    ULIDEntity,
    AggregateRoot,
    BaseValueObject,
)

# Events
from core.base.events import (
    DomainEvent,
    EntityCreatedEvent,
    EntityUpdatedEvent,
    EntityDeletedEvent,
    EventBus,
    IntegrationEvent,
)

# Repository
from core.base.repository import (
    IRepository,
    InMemoryRepository,
)

# CQRS
from core.base.cqrs import BaseCommand, BaseQuery

# Patterns
from core.base.patterns import (
    # Result
    Result,
    Ok,
    Err,
    collect_results,
    # Specification
    Specification,
    AndSpecification,
    OrSpecification,
    NotSpecification,
    TrueSpecification,
    FalseSpecification,
    PredicateSpecification,
    AttributeSpecification,
    # Validation
    Validator,
    ValidationError,
    FieldError,
    CompositeValidator,
    ChainedValidator,
    PredicateValidator,
    RangeValidator,
    validate_all,
    # UoW
    UnitOfWork,
    # Pagination
    CursorPage,
    CursorPagination,
)

__all__ = [
    # Domain
    "BaseEntity",
    "AuditableEntity",
    "VersionedEntity",
    "AuditableVersionedEntity",
    "ULIDEntity",
    "AggregateRoot",
    "BaseValueObject",
    # Events
    "DomainEvent",
    "EntityCreatedEvent",
    "EntityUpdatedEvent",
    "EntityDeletedEvent",
    "EventBus",
    "IntegrationEvent",
    # Repository
    "IRepository",
    "InMemoryRepository",
    # CQRS
    "BaseCommand",
    "BaseQuery",
    # Result
    "Result",
    "Ok",
    "Err",
    "collect_results",
    # Specification
    "Specification",
    "AndSpecification",
    "OrSpecification",
    "NotSpecification",
    "TrueSpecification",
    "FalseSpecification",
    "PredicateSpecification",
    "AttributeSpecification",
    # Validation
    "Validator",
    "ValidationError",
    "FieldError",
    "CompositeValidator",
    "ChainedValidator",
    "PredicateValidator",
    "RangeValidator",
    "validate_all",
    # UoW
    "UnitOfWork",
    # Pagination
    "CursorPage",
    "CursorPagination",
]
