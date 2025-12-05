"""Application constants.

Centralizes magic numbers and configuration defaults.

**Feature: code-review-2025**
**Validates: Quality Standards - No magic numbers
"""

from typing import Final

# =============================================================================
# Request Size Limits (bytes)
# =============================================================================
DEFAULT_REQUEST_SIZE_BYTES: Final[int] = 10 * 1024 * 1024  # 10MB
UPLOAD_REQUEST_SIZE_BYTES: Final[int] = 50 * 1024 * 1024  # 50MB
IMPORT_REQUEST_SIZE_BYTES: Final[int] = 20 * 1024 * 1024  # 20MB

# =============================================================================
# Cache TTL (seconds)
# =============================================================================
JWKS_CACHE_MAX_AGE_SECONDS: Final[int] = 300  # 5 minutes
JWKS_STALE_WHILE_REVALIDATE_SECONDS: Final[int] = 60  # 1 minute
OPENID_CONFIG_CACHE_MAX_AGE_SECONDS: Final[int] = 3600  # 1 hour

# =============================================================================
# Token Expiration (seconds)
# =============================================================================
ACCESS_TOKEN_EXPIRE_SECONDS: Final[int] = 3600  # 1 hour
REFRESH_TOKEN_EXPIRE_SECONDS: Final[int] = 86400 * 7  # 7 days
DEFAULT_TOKEN_TTL_SECONDS: Final[int] = 604800  # 7 days

# =============================================================================
# Rate Limiting
# =============================================================================
DEFAULT_RATE_LIMIT_REQUESTS: Final[int] = 100
READ_RATE_LIMIT_REQUESTS: Final[int] = 100
WRITE_RATE_LIMIT_REQUESTS: Final[int] = 20
DELETE_RATE_LIMIT_REQUESTS: Final[int] = 10

# =============================================================================
# Pagination
# =============================================================================
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100
MIN_PAGE_NUMBER: Final[int] = 1

# =============================================================================
# CORS
# =============================================================================
CORS_MAX_AGE_SECONDS: Final[int] = 86400  # 24 hours
CORS_PREFLIGHT_MAX_AGE_SECONDS: Final[int] = 3600  # 1 hour

# =============================================================================
# Infrastructure Defaults
# =============================================================================
STORAGE_TTL_MIN_SECONDS: Final[int] = 1
STORAGE_TTL_MAX_SECONDS: Final[int] = 86400  # 24 hours
STORAGE_TTL_DEFAULT_SECONDS: Final[int] = 3600  # 1 hour
PRESIGNED_URL_EXPIRE_SECONDS: Final[int] = 3600  # 1 hour
MAX_STORAGE_LIST_KEYS: Final[int] = 100

# =============================================================================
# Field Limits
# =============================================================================
MAX_DISPLAY_NAME_LENGTH: Final[int] = 100
MIN_EMAIL_LENGTH: Final[int] = 5
MAX_EMAIL_LENGTH: Final[int] = 255
MIN_PASSWORD_LENGTH: Final[int] = 8
MAX_PASSWORD_LENGTH: Final[int] = 128

# =============================================================================
# HTTP Status Codes (for clarity in non-FastAPI contexts)
# =============================================================================
HTTP_OK: Final[int] = 200
HTTP_BAD_REQUEST: Final[int] = 400
HTTP_UNPROCESSABLE_ENTITY: Final[int] = 422
HTTP_INTERNAL_SERVER_ERROR: Final[int] = 500
HTTP_SERVICE_UNAVAILABLE: Final[int] = 503
