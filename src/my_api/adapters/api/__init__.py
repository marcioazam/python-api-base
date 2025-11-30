"""API adapters - Routes, middleware, dependencies.

This module provides HTTP API adapters including REST routes,
middleware components, and API versioning infrastructure.
"""

from my_api.adapters.api.versioning import (
    APIVersion,
    DeprecationHeaderMiddleware,
    VersionConfig,
    VersionedRouter,
)

__all__ = [
    "APIVersion",
    "DeprecationHeaderMiddleware",
    "VersionConfig",
    "VersionedRouter",
]
