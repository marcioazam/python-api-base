"""User aggregate root.

Contains the UserAggregate entity representing the user domain model.

**Feature: domain-restructuring-2025**
"""

from domain.users.aggregates.aggregates import UserAggregate

__all__ = [
    "UserAggregate",
]
