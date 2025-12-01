"""Auto-Ban System for automatic blocking after threshold violations.

**Feature: file-size-compliance-phase2, Task 2.3**
**Validates: Requirements 1.3, 5.1, 5.2, 5.3**

Provides automatic ban system that tracks violations and bans
users/IPs after exceeding configurable thresholds.
"""

from .config import AutoBanConfig, AutoBanConfigBuilder
from .detector import (
    AutoBanService,
    create_auto_ban_service,
    create_lenient_config,
    create_strict_config,
)
from .enums import BanStatus, ViolationType
from .models import BanCheckResult, BanRecord, BanThreshold, Violation
from .store import BanStore, InMemoryBanStore

__all__ = [
    "AutoBanConfig",
    "AutoBanConfigBuilder",
    "AutoBanService",
    "BanCheckResult",
    "BanRecord",
    "BanStatus",
    "BanStore",
    "BanThreshold",
    "InMemoryBanStore",
    "Violation",
    "ViolationType",
    "create_auto_ban_service",
    "create_lenient_config",
    "create_strict_config",
]
