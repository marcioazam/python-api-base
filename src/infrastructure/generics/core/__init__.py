"""Generic infrastructure components.

Contains configuration, error handling, protocols, status, and validators.

**Feature: infrastructure-restructuring-2025**
"""

from infrastructure.generics.core.config import GenericConfig
from infrastructure.generics.core.errors import GenericError
from infrastructure.generics.core.protocols import GenericProtocol
from infrastructure.generics.core.status import Status
from infrastructure.generics.core.validators import validate

__all__ = [
    "GenericConfig",
    "GenericError",
    "GenericProtocol",
    "Status",
    "validate",
]
