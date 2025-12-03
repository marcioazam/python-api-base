"""Fallback pattern re-exports.

**Feature: infrastructure-modules-workflow-analysis**
**Validates: Requirements 1.3**

This module provides backward-compatible imports for fallback components.
All implementations are in patterns.py.
"""

from infrastructure.resilience.patterns import Fallback

__all__ = [
    "Fallback",
]
