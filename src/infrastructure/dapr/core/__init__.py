"""Dapr core components.

Contains Dapr client, error handling, health checks, and middleware.

**Feature: infrastructure-restructuring-2025**
"""

from infrastructure.dapr.core.client import DaprClient
from infrastructure.dapr.core.errors import DaprError
from infrastructure.dapr.core.health import HealthCheck
from infrastructure.dapr.core.middleware import DaprMiddleware

__all__ = [
    "DaprClient",
    "DaprError",
    "HealthCheck",
    "DaprMiddleware",
]
