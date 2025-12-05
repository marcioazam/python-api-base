"""Feature flag service and strategy management.

Contains the main feature flag service and strategy re-exports.

**Feature: application-services-restructuring-2025**
"""

from application.services.feature_flags.service.service import FeatureFlagService

__all__ = [
    "FeatureFlagService",
]
