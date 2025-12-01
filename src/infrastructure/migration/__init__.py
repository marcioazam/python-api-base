"""Migration infrastructure module.

Provides migration patterns including strangler fig for legacy system migration.

**Feature: python-api-base-2025-review**
"""

from src.infrastructure.migration.strangler_fig import (
    StranglerFigConfig,
    StranglerFigRouter,
    MigrationPhase,
)

__all__ = [
    "StranglerFigConfig",
    "StranglerFigRouter",
    "MigrationPhase",
]
