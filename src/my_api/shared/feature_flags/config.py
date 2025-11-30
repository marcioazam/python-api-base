"""feature_flags configuration."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from .enums import FlagStatus


@dataclass
class FlagConfig:
    """Feature flag configuration.

    Attributes:
        key: Flag unique key.
        name: Human-readable name.
        description: Flag description.
        status: Current status.
        default_value: Default value when disabled.
        enabled_value: Value when enabled.
        percentage: Rollout percentage (0-100).
        user_ids: Specific user IDs to enable for.
        groups: Groups to enable for.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    key: str
    name: str = ""
    description: str = ""
    status: FlagStatus = FlagStatus.DISABLED
    default_value: Any = False
    enabled_value: Any = True
    percentage: float = 0.0
    user_ids: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
