"""Core configuration module.

Organized into subpackages by responsibility:
- application/: Application settings and constants
- infrastructure/: Database, gRPC, Dapr configurations
- security/: Security and authentication settings
- observability/: Logging and observability settings
- shared/: Shared utilities

**Refactored: 2025 - Split settings.py (457 lines) into focused modules**
"""

from core.config.application import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    CORS_MAX_AGE_SECONDS,
    CORS_PREFLIGHT_MAX_AGE_SECONDS,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RATE_LIMIT_REQUESTS,
    DEFAULT_REQUEST_SIZE_BYTES,
    DEFAULT_TOKEN_TTL_SECONDS,
    DELETE_RATE_LIMIT_REQUESTS,
    IMPORT_REQUEST_SIZE_BYTES,
    UPLOAD_REQUEST_SIZE_BYTES,
    WRITE_RATE_LIMIT_REQUESTS,
    READ_RATE_LIMIT_REQUESTS,
    REFRESH_TOKEN_EXPIRE_SECONDS,
    Settings,
    get_settings,
)
from core.config.infrastructure import DatabaseSettings
from core.config.observability import ObservabilitySettings
from core.config.security import RATE_LIMIT_PATTERN, RedisSettings, SecuritySettings
from core.config.shared import redact_url_credentials

__all__ = [
    # Constants
    "ACCESS_TOKEN_EXPIRE_SECONDS",
    "CORS_MAX_AGE_SECONDS",
    "CORS_PREFLIGHT_MAX_AGE_SECONDS",
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_RATE_LIMIT_REQUESTS",
    "DEFAULT_REQUEST_SIZE_BYTES",
    "DEFAULT_TOKEN_TTL_SECONDS",
    "DELETE_RATE_LIMIT_REQUESTS",
    "IMPORT_REQUEST_SIZE_BYTES",
    "JWKS_CACHE_MAX_AGE_SECONDS",
    "JWKS_STALE_WHILE_REVALIDATE_SECONDS",
    "MAX_DISPLAY_NAME_LENGTH",
    "MAX_EMAIL_LENGTH",
    "MAX_PAGE_SIZE",
    "MAX_PASSWORD_LENGTH",
    "MAX_STORAGE_LIST_KEYS",
    "MIN_EMAIL_LENGTH",
    "MIN_PAGE_NUMBER",
    "MIN_PASSWORD_LENGTH",
    "OPENID_CONFIG_CACHE_MAX_AGE_SECONDS",
    "PRESIGNED_URL_EXPIRE_SECONDS",
    # Settings
    "RATE_LIMIT_PATTERN",
    "READ_RATE_LIMIT_REQUESTS",
    "REFRESH_TOKEN_EXPIRE_SECONDS",
    "STORAGE_TTL_DEFAULT_SECONDS",
    "STORAGE_TTL_MAX_SECONDS",
    "STORAGE_TTL_MIN_SECONDS",
    "UPLOAD_REQUEST_SIZE_BYTES",
    "WRITE_RATE_LIMIT_REQUESTS",
    "DatabaseSettings",
    "ObservabilitySettings",
    "RedisSettings",
    "SecuritySettings",
    "Settings",
    "get_settings",
    "redact_url_credentials",
]
