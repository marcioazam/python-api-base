"""feature_flags models."""

from dataclasses import dataclass, field
from typing import Any



@dataclass
class EvaluationContext:
    """Context for flag evaluation.

    Attributes:
        user_id: Current user ID.
        groups: User's groups.
        attributes: Additional attributes.
    """

    user_id: str | None = None
    groups: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
