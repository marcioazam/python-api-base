"""Shared configuration patterns for infrastructure modules.

**Feature: infrastructure-generics-review-2025**
**Validates: Requirements 14.5**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self


@dataclass
class BaseConfig:
    """Base configuration class for infrastructure modules.

    Provides common configuration patterns that can be extended
    by specific modules.

    Attributes:
        enabled: Whether the feature is enabled.
        debug: Enable debug mode.
        timeout: Default timeout in seconds.
        retry_attempts: Number of retry attempts.
        metadata: Additional configuration metadata.
    """

    enabled: bool = True
    debug: bool = False
    timeout: float = 30.0
    retry_attempts: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


class ConfigBuilder[TConfig]:
    """Generic configuration builder.

    Type Parameters:
        TConfig: The configuration type being built.

    Example:
        >>> builder = ConfigBuilder[CacheConfig]()
        >>> config = builder.with_timeout(60).with_retry(5).build()
    """

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def with_value(self, key: str, value: Any) -> Self:
        """Set a configuration value."""
        self._values[key] = value
        return self

    def with_timeout(self, timeout: float) -> Self:
        """Set timeout value."""
        self._values["timeout"] = timeout
        return self

    def with_retry(self, attempts: int) -> Self:
        """Set retry attempts."""
        self._values["retry_attempts"] = attempts
        return self

    def with_debug(self, enabled: bool = True) -> Self:
        """Enable or disable debug mode."""
        self._values["debug"] = enabled
        return self

    def with_metadata(self, key: str, value: Any) -> Self:
        """Add metadata entry."""
        if "metadata" not in self._values:
            self._values["metadata"] = {}
        self._values["metadata"][key] = value
        return self

    def build(self, config_class: type[TConfig]) -> TConfig:
        """Build the configuration instance.

        Args:
            config_class: The configuration class to instantiate.

        Returns:
            Configuration instance with set values.
        """
        return config_class(**self._values)

    def get_values(self) -> dict[str, Any]:
        """Get all configured values."""
        return self._values.copy()
