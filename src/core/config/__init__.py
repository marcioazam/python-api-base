"""Core configuration module.

**Refactored: 2025 - Split settings.py (457 lines) into focused modules**
"""

from core.config.database import DatabaseSettings
from core.config.observability import ObservabilitySettings
from core.config.security import RATE_LIMIT_PATTERN, RedisSettings, SecuritySettings
from core.config.settings import Settings, get_settings
from core.config.utils import redact_url_credentials

__all__ = [
    "DatabaseSettings",
    "ObservabilitySettings",
    "RATE_LIMIT_PATTERN",
    "RedisSettings",
    "SecuritySettings",
    "Settings",
    "get_settings",
    "redact_url_credentials",
]
