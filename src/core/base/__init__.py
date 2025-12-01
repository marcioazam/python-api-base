"""Core base classes for the application.

**Feature: architecture-restructuring-2025**
"""

# Lazy imports to avoid circular dependencies
__all__ = [
    "AggregateRoot",
    "BaseCommand",
    "BaseEntity",
    "BaseQuery",
    "BaseValueObject",
    "DomainEvent",
    "Err",
    "EventBus",
    "IntegrationEvent",
    "Ok",
    "Result",
    "ULIDEntity",
    "UnitOfWork",
    "event_bus",
]
