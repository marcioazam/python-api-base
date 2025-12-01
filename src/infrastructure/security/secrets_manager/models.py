"""Secrets manager models.

**Feature: code-review-refactoring, Task 18.1: Refactor secrets_manager.py**
**Validates: Requirements 5.7**
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel

from .enums import SecretType


@dataclass(frozen=True, slots=True)
class SecretMetadata:
    """Metadata about a secret."""

    name: str
    version: str = "AWSCURRENT"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    rotation_enabled: bool = False
    next_rotation: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


class SecretValue(BaseModel):
    """Secret value container."""

    value: str | dict[str, Any]
    secret_type: SecretType = SecretType.STRING
    metadata: SecretMetadata | None = None

    model_config = {"arbitrary_types_allowed": True}


@dataclass
class RotationConfig:
    """Secret rotation configuration."""

    enabled: bool = False
    interval_days: int = 30
    rotation_lambda_arn: str | None = None
    auto_rotate_on_access: bool = False
