"""Base Command class for CQRS pattern.

Commands represent intentions to change the system state.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.1**
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

try:
    from my_app.shared.utils.time import utc_now
except ImportError:
    from datetime import timezone
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class BaseCommand(ABC):
    """Base class for all commands in CQRS pattern.
    
    Commands are immutable objects that represent an intention to
    change the system state. They should:
    - Be named with imperative verbs (CreateUser, UpdateOrder)
    - Contain all data needed to perform the action
    - Be validated before execution
    
    Attributes:
        command_id: Unique identifier for the command.
        timestamp: When the command was created.
        correlation_id: ID for tracing related operations.
        user_id: ID of the user issuing the command (for audit).
    """
    
    command_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)
    correlation_id: str | None = None
    user_id: str | None = None
    
    @property
    def command_type(self) -> str:
        """Return the command type identifier."""
        return self.__class__.__name__
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize command to dictionary.
        
        Returns:
            Dictionary representation of the command.
        """
        from dataclasses import asdict
        return asdict(self)
