"""Generic infrastructure protocols and utilities.

**Feature: infrastructure-generics-review-2025**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 3.1, 4.1**

This module provides:
- Generic protocols for Repository, Service, Factory, Store patterns
- Centralized error messages and typed error classes
- Standardized status enums for all infrastructure modules
- Shared validation utilities and configuration patterns
"""

from .protocols import (
    Repository,
    Service,
    Factory,
    Store,
    AsyncRepository,
    AsyncService,
)
from .errors import (
    ErrorMessages,
    InfrastructureError,
    AuthenticationError,
    CacheError,
    PoolError,
    ValidationError,
    SecurityError,
    MessagingError,
)
from .status import (
    BaseStatus,
    ConnectionStatus,
    TaskStatus,
    HealthStatus,
    CacheStatus,
)
from .validators import (
    validate_non_empty,
    validate_range,
    validate_format,
    validate_required,
    ValidationResult,
)
from .config import (
    BaseConfig,
    ConfigBuilder,
)

__all__ = [
    # Protocols
    "Repository",
    "Service",
    "Factory",
    "Store",
    "AsyncRepository",
    "AsyncService",
    # Errors
    "ErrorMessages",
    "InfrastructureError",
    "AuthenticationError",
    "CacheError",
    "PoolError",
    "ValidationError",
    "SecurityError",
    "MessagingError",
    # Status Enums
    "BaseStatus",
    "ConnectionStatus",
    "TaskStatus",
    "HealthStatus",
    "CacheStatus",
    # Validators
    "validate_non_empty",
    "validate_range",
    "validate_format",
    "validate_required",
    "ValidationResult",
    # Config
    "BaseConfig",
    "ConfigBuilder",
]
