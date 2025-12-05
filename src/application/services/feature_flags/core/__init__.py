"""Core feature flag types and base classes.

Contains base protocol and enumerations for feature flag strategies.

**Feature: application-services-restructuring-2025**
"""

from application.services.feature_flags.core.enums import FlagStatus, RolloutStrategy

__all__ = [
    "FlagStatus",
    "RolloutStrategy",
]
