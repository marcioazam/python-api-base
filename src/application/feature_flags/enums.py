"""feature_flags enums."""

from enum import Enum


class FlagStatus(str, Enum):
    """Feature flag status."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    PERCENTAGE = "percentage"
    TARGETED = "targeted"

class RolloutStrategy(str, Enum):
    """Rollout strategy types."""

    ALL = "all"
    NONE = "none"
    PERCENTAGE = "percentage"
    USER_IDS = "user_ids"
    GROUPS = "groups"
    CUSTOM = "custom"
