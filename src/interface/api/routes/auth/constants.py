"""Auth constants.

WARNING: Demo users are for development/testing only.
Do NOT use in production environments.
"""

import logging
import os

logger = logging.getLogger(__name__)

# Demo users for development/testing only
DEMO_USERS = {
    "admin": {"password": "admin123", "roles": ["admin"]},
    "user": {"password": "user123", "roles": ["user"]},
    "viewer": {"password": "viewer123", "roles": ["viewer"]},
}


def _check_production_warning() -> None:
    """Log warning if demo users are used in production."""
    # Check common production indicators
    is_production = (
        os.getenv("ENVIRONMENT", "").lower() in ("production", "prod")
        or os.getenv("DEBUG", "true").lower() == "false"
        or os.getenv("APP_ENV", "").lower() == "production"
    )

    if is_production:
        logger.warning(
            "SECURITY WARNING: Demo users with hardcoded passwords are being "
            "loaded in a production environment. This is a security risk. "
            "Please configure proper authentication."
        )


# Check on module load
_check_production_warning()
