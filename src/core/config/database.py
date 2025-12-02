"""Database configuration settings.

**Feature: core-code-review**
**Refactored: 2025 - Extracted from settings.py for SRP compliance**
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .utils import redact_url_credentials


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(env_prefix="DATABASE__")

    url: str = Field(
        default="postgresql+asyncpg://localhost/mydb",
        description="Database connection URL",
    )
    pool_size: int = Field(default=5, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(
        default=10, ge=0, le=100, description="Max overflow connections"
    )
    echo: bool = Field(default=False, description="Echo SQL statements")

    def get_safe_url(self) -> str:
        """Get URL with credentials redacted for logging."""
        return redact_url_credentials(self.url)

    def __repr__(self) -> str:
        """Safe representation without credentials."""
        return (
            f"DatabaseSettings(url='{self.get_safe_url()}', pool_size={self.pool_size})"
        )
