"""Feature flags service for controlled feature rollouts.

Provides feature flag management with percentage-based rollouts,
user targeting, and custom evaluation rules.

**Feature: enterprise-features-2025**
**Validates: Requirements 10.1, 10.2, 10.3**
"""

from .enums import FlagStatus, RolloutStrategy
from .models import EvaluationContext
from .config import FlagConfig
from .service import FeatureFlagService

__all__ = [
    # Enums
    "FlagStatus",
    "RolloutStrategy",
    # Models
    "EvaluationContext",
    "FlagConfig",
    # Service
    "FeatureFlagService",
]
