"""Core base classes for the application.

**Feature: architecture-restructuring-2025**
**Feature: python-api-base-2025-generics-audit**
"""

# Lazy imports to avoid circular dependencies
__all__ = [
    # Aggregate & Entity
    "AggregateRoot",
    "AuditableEntity",
    "AuditableVersionedEntity",
    "BaseEntity",
    "ULIDEntity",
    "VersionedEntity",
    # Commands & Queries
    "BaseCommand",
    "BaseQuery",
    # Domain Events
    "DomainEvent",
    "EventBus",
    "IntegrationEvent",
    "event_bus",
    # Result Pattern
    "Err",
    "Ok",
    "Result",
    "collect_results",
    "result_from_dict",
    # Validation
    "ChainedValidator",
    "CompositeValidator",
    "FieldError",
    "PredicateValidator",
    "RangeValidator",
    "ValidationError",
    "Validator",
    "validate_all",
    # Specification Pattern
    "AndSpecification",
    "AttributeSpecification",
    "FalseSpecification",
    "NotSpecification",
    "OrSpecification",
    "PredicateSpecification",
    "Specification",
    "TrueSpecification",
    # Repository & UoW
    "IRepository",
    "UnitOfWork",
    # Other
    "BaseValueObject",
]
