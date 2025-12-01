"""Generic connection pooling with health checking and auto-recovery.

**Feature: api-architecture-analysis, Task 12.1: Connection Pooling Manager**
**Validates: Requirements 6.1, 6.4**

Provides type-safe connection pooling with health checking and auto-recovery.

**Feature: full-codebase-review-2025, Task 1.1: Refactored for file size compliance**
"""

from .config import PoolConfig
from .constants import *
from .enums import ConnectionState
from .errors import (
    AcquireTimeoutError,
    ConnectionError,
    PoolError,
    PoolExhaustedError,
)
from .factory import BaseConnectionFactory, ConnectionFactory
from .models import ConnectionInfo
from .service import ConnectionPool, ConnectionPoolContext
from .stats import PoolStats

__all__ = [
    "AcquireTimeoutError",
    "BaseConnectionFactory",
    "ConnectionError",
    "ConnectionFactory",
    "ConnectionInfo",
    "ConnectionPool",
    "ConnectionPoolContext",
    "ConnectionState",
    "PoolConfig",
    "PoolError",
    "PoolExhaustedError",
    "PoolStats",
]
