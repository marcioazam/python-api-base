"""System-related infrastructure exceptions.

**Feature: infrastructure-code-review**
**Validates: Requirements 8.2, 10.3**
"""

from infrastructure.errors.base import InfrastructureError


class TelemetryError(InfrastructureError):
    """Telemetry/observability error.

    Raised when telemetry operations fail, such as
    metric collection or trace export failures.
    """

    pass


class ConfigurationError(InfrastructureError):
    """Configuration error.

    Raised when configuration is invalid or missing.
    """

    pass
