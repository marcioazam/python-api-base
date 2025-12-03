"""Timeout pattern re-exports.

**Feature: infrastructure-modules-workflow-analysis**
**Validates: Requirements 1.3**

This module provides backward-compatible imports for timeout components.
All implementations are in patterns.py.
"""

from infrastructure.resilience.patterns import (
    Timeout,
    TimeoutConfig,
)

__all__ = [
    "Timeout",
    "TimeoutConfig",
]
